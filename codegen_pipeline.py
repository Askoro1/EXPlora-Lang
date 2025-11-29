import uuid
from .ai_gen_helpers.plan_gen import generate_plan
from .ai_gen_helpers.plan_validation import *
from .ai_gen_helpers.code_validation import generate_validated_code_from_plan

MAX_RETRIES = 10  # LLM will retry generating the plan this many times


def codegen_pipeline(prompt: str, context, manual_check: bool = True, generator_name: str = "GENERATOR_MODEL", judge_name: str = "JUDGE_MODEL",):
    run_id = str(uuid.uuid4())

    curr_attempt = 0

    with open("./EXPlora-Lang/ai_gen_helpers/DOCUMENTATION.txt", "r") as documentation_file:
        documentation = documentation_file.read()

    # Generate the plan
    plan_dict = generate_plan(prompt, current_func_context=str(context), program_context=str(context), documentation=documentation)
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
            attempt=curr_attempt,
            validity="valid",
            reason="",
            plan_txt=plan_str,
            mode=mode,
            generator_name=generator_name,
            judge_name=judge_name,
        )
        print("Plan was valid.")
        plan = plan_result
    else:
        # Otherwise it means the plan was invalid
        error_msg = "; ".join(errors or ["unknown validation error"])

        if manual_check:
            # Manual correction loop: keep editing until valid or user cancels
            while True:
                curr_attempt += 1
                log_plan_attempt(
                    run_id=run_id,
                    attempt=curr_attempt,
                    validity="invalid",
                    reason=error_msg,
                    plan_txt=plan_str,
                    mode=mode,
                )

                edited_plan = manual_edit(plan_str, errors or [])
                if edited_plan is None:
                    raise RuntimeError(
                        f"No valid plan and manual edit cancelled (run_id={run_id})."
                    )

                ok2, errors2, plan_result2 = validate_plan_json(edited_plan)

                if ok2 and plan_result2 is not None:
                    log_plan_attempt(
                        run_id=run_id,
                        attempt=curr_attempt,
                        validity="valid",
                        reason="manual correction",
                        plan_txt=edited_plan,
                        mode=mode,
                    )
                    print("Plan became valid after manual correction.")

                    plan = plan_result2
                    break
                else:
                    # if still invalid, update state and loop again
                    error_msg = "; ".join(errors2 or ["unknown validation error"])
                    errors = errors2[:]
                    plan_str = edited_plan
        else:
            judge_feedback = None  # This gets used later if the plan fails validation

            for _ in range(MAX_RETRIES):
                # Auto-retry path (LLM judge + generator) - skeleton
                curr_attempt += 1
                log_plan_attempt(
                    run_id=run_id,
                    attempt=curr_attempt,
                    validity="invalid",
                    reason=error_msg,
                    plan_txt=plan_str,
                    mode=mode,
                    generator_name=generator_name,
                    judge_name=judge_name,
                )
                print("Plan was invalid : LLM Check.")
                # TODO: call judge LLM here and update judge_feedback for next attempt
                judge_feedback = error_msg

                # This part will be similar to the manual check

                plan_result2 = None

            if ok and plan_result2 is not None:
                plan = plan_result2
            else:
                # If we get here, no valid plan after all retries
                raise RuntimeError(f"No valid plan found after {MAX_RETRIES} attempts (run_id={run_id}).")

    # Code generation
    print("\n--- Generating EXPlora Code... ---\n")
    code = generate_validated_code_from_plan(plan, documentation=documentation)
    print("\n--- Generated EXPlora Code ---\n")
    print(code)
    return {"plan": plan, "code": code}


if __name__ == "__main__":
    user_request = "Read a CSV file, group by `category` column and calculate mean value by `value` column, then plot a bar chart"
    codegen_pipeline(user_request, "None", manual_check=True, generator_name="GENERATOR_MODEL", judge_name="JUDGE_MODEL")