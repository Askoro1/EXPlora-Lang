from datetime import datetime, timezone
import tempfile
import subprocess
import uuid
import json
import os

from ..plangeneration.plan_gen import generate_plan
from ..plangeneration.plan_judge import generate_judge_feedback
from ..planvalidation.plan_validation import validate_plan_json
from ..codegeneration.code_gen import generate_explora_code

MAX_RETRIES = 10  # LLM will retry generating the plan this many times
LOG_FILE = "plan_runs.jsonl"  # one JSON per line

def manual_edit(original_plan: str, errors: list[str]) -> str | None:
    """
    Basic version for manual editing.
    Opens a temp file, writes the errors and the plan in it.
    After the user modifies the plan, the temp file is closed and the new plan is validated.
    """
    print("Plan is invalid. Opening it for manual correction...")

    # Display the original plan and validation errors in a readable form
    # to assist the user in understanding what needs to be fixed.  If
    # the plan parses as JSON we pretty‑print it; otherwise we show it
    # verbatim.
    try:
        parsed_plan = json.loads(original_plan)
        pretty_plan = json.dumps(parsed_plan, indent=4, ensure_ascii=False)
    except Exception:
        pretty_plan = original_plan
    print("\n=== Current Plan ===")
    print(pretty_plan)
    if errors:
        print("\n=== Validation Errors ===")
        for e in errors:
            print(f" - {e}")

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

        # Write the original plan first
        tmp.write(original_plan)
        tmp.write("\n\n")
        tmp.write("// --- Validation errors (for your reference) ---\n")
        for e in errors:
            tmp.write(f"// {e}\n")

    # Use PyCharm (or whatever EDITOR is set to)
    editor = os.environ.get("EDITOR") or "pycharm64.exe"
    subprocess.run([editor, tmp_path])

    # Read edited file
    with open(tmp_path, "r", encoding="utf-8") as f:
        edited = f.readlines()

    # Strip comment lines (starting with //) before returning to validator
    cleaned_lines = [
        line for line in edited
        if not line.lstrip().startswith("//")
    ]
    cleaned = "".join(cleaned_lines)

    return cleaned

def log_plan_attempt(run_id: str, attempt: int, validity: str, reason: str, plan_txt: str, mode: str, generator_name: str = "GENERATOR_NOT_SET", judge_name: str = "JUDGE_NOT_SET", ) -> None:
    """
    Logs the attempt with relevant information.
    """
    entry = {
        "run_id": run_id,
        "attempt": attempt,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generator": generator_name,
        "judge": judge_name,
        "validity": validity,
        "reason": reason,
        "plan": plan_txt,
        "mode": mode,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry))
        f.write("\n")

def run_pipeline(prompt: str, context, manual_check: bool = False, generator_name: str = "GENERATOR_MODEL", judge_name: str = "JUDGE_MODEL",):
    run_id = str(uuid.uuid4())
    judge_feedback = None  # This gets used later if the plan fails validation

    for attempt in range(1, MAX_RETRIES + 1):
        # Generate the plan.  On subsequent attempts, if the previous plan
        # failed validation the judge may have provided feedback stored
        # in `judge_feedback`.  We pass this into the `dev_notes`
        # argument of `generate_plan` to guide the planner towards a
        # corrected plan.  When `judge_feedback` is None or empty, an
        # empty string is passed.
        plan_dict = generate_plan(
            request=prompt,
            current_func_context=str(context),
            program_context=str(context),
            dev_notes=judge_feedback or "",
        )
        plan_str = json.dumps(plan_dict)

        # Validate the plan
        ok, errors, plan_result = validate_plan_json(plan_str)

        if manual_check:
            mode = "MANUAL"
        else:
            mode = "LLM"

        # If there's a valid plan
        if ok and plan_result is not None:
            log_plan_attempt(
                run_id=run_id,
                attempt=attempt,
                validity="valid",
                reason="",
                plan_txt=plan_str,
                mode=mode,
                generator_name=generator_name,
                judge_name=judge_name,
            )
            print("Plan was valid.")

            # Code generation
            code = generate_explora_code(plan_result)
            print("\n--- Generated EXPlora Code ---\n")
            print(code)

            return {"plan": plan_result, "code": code}

        # Otherwise it means the plan was invalid
        error_msg = "; ".join(errors or ["unknown validation error"])

        if manual_check:
            # Manual correction loop: keep editing until valid or user cancels
            while True:
                log_plan_attempt(
                    run_id=run_id,
                    attempt=attempt,
                    validity="invalid",
                    reason=error_msg,
                    plan_txt=plan_str,
                    mode=mode,
                )
                print("Plan was invalid : Manual Check.")

                edited_plan = manual_edit(plan_str, errors or [])
                if edited_plan is None:
                    raise RuntimeError(
                        f"No valid plan and manual edit cancelled (run_id={run_id})."
                    )

                ok2, errors2, plan_result2 = validate_plan_json(edited_plan)

                if ok2 and plan_result2 is not None:
                    log_plan_attempt(
                        run_id=run_id,
                        attempt=attempt,
                        validity="valid",
                        reason="manual correction",
                        plan_txt=edited_plan,
                        mode=mode,
                    )
                    print("Plan became valid after manual correction.")

                    # Code generation
                    code = generate_explora_code(plan_result2)
                    print("\n--- Generated EXPlora Code ---\n")
                    print(code)

                    return {"plan": plan_result2, "code": code}

                # if still invalid, update state and loop again
                error_msg = "; ".join(errors2 or ["unknown validation error"])
                errors = errors2
                plan_str = edited_plan
        else:
            # Auto-retry path (LLM judge + generator).  Log the invalid
            # plan and call the judge to obtain feedback.  The feedback
            # will be used in the next iteration via the `dev_notes`
            # parameter of `generate_plan`.
            log_plan_attempt(
                run_id=run_id,
                attempt=attempt,
                validity="invalid",
                reason=error_msg,
                plan_txt=plan_str,
                mode=mode,
                generator_name=generator_name,
                judge_name=judge_name,
            )
            print("Plan was invalid : LLM Check.")

            # Attempt to get feedback from the judge.  If the judge
            # fails (e.g. due to missing API keys) we fall back to
            # using the error message itself as guidance.
            try:
                judge_feedback = generate_judge_feedback(plan_str, errors or [])
            except Exception as e:
                judge_feedback = error_msg
                print(f"Judge call failed: {e}. Falling back to error message.")

            # Print the judge's feedback so the user can see what is
            # guiding the next generation step.
            print("\n=== Judge Feedback ===")
            print(judge_feedback)

            # Continue to next attempt (loop), which will regenerate the
            # plan with the feedback provided.  No further action is
            # needed here.

    # If we get here, no valid plan after all retries
    raise RuntimeError(
        f"No valid plan found after {MAX_RETRIES} attempts (run_id={run_id})."
    )