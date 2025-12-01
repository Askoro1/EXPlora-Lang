import uuid

from .ai_gen_helpers.plan_gen import generate_plan
from .ai_gen_helpers.plan_validation import *
from .ai_gen_helpers.code_validation import *


MAX_RETRIES = 5  # LLM will retry generating the plan this many times


def replace_first_ai_block(code: str, replacement: str) -> str:
    prompt = f"""
    You are an EXPlora-Lang programming language code editor.

    Your task:
    1. In the ORIGINAL CODE, find the **first occurrence** of a block in the format:
       AI("...")

    2. Determine its **exact indentation** (spaces or tabs before AI).

    3. Replace that entire AI(...) block with the provided REPLACEMENT SNIPPET,
       preserving the **exact same indentation for every line** of the inserted snippet.

    4. Keep **everything else in the file exactly the same**.

    ⚠️ Strict rules:
    - Replace ONLY the FIRST occurrence of AI(...)
    - Preserve all formatting and spacing outside the replaced block
    - The replacement snippet must be indented exactly to match the original AI(...) line
    - Output ONLY the final, modified code
    - Output must be wrapped in exactly three backticks
    - Do NOT explain anything

    REPLACEMENT SNIPPET (not yet indented):
    {replacement}

    ORIGINAL CODE:
    {code}
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1
        )
    )

    return response.text.strip()


def codegen_pipeline(prompt: str, code: str = "None", context_strategy: str = "None", plan_check: str = "manual", generator_name: str = "GENERATOR_MODEL", judge_name: str = "JUDGE_MODEL",):
    run_id = str(uuid.uuid4())

    curr_attempt = 0

    with open("./EXPlora-Lang/ai_gen_helpers/DOCUMENTATION.txt", "r") as documentation_file:
        documentation = documentation_file.read()

    context = None

    # Create context
    if context_strategy == "full":
        context = code[:]
    elif context_strategy == "left":
        start = code.find('AI("')
        context = code[:start]
    else:
        context = "None"

    print(f"Context:\n{context}")

    # Generate the plan
    plan = generate_plan(prompt, context=context, documentation=documentation)
    plan_str = json.dumps(plan)

    # Validate the plan
    ok, errors, plan_result = validate_plan_json(plan_str)

    if plan_check == "manual":
        mode = "MANUAL"
    elif plan_check == "LLM":
        mode = "LLM"
    else:
        mode = "both"

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
        print("\nPlan is valid.\n")

        plan = plan_result

        ans = input("Would you like to check the plan (y/n)? ")
        if ans == "y":
            edited_plan = manual_edit_plan(plan, [])
            if edited_plan is None:
                raise RuntimeError(
                    f"No valid plan and manual edit cancelled (run_id={run_id})."
                )
            plan = edited_plan
    else:
        # Otherwise it means the plan was invalid
        error_msg = "; ".join(errors or ["unknown validation error"])

        if plan_check == "LLM" or plan_check == "both":
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

        if plan_check == "manual" or plan_check == "both":
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

                edited_plan = manual_edit_plan(plan, errors or [])
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

    # Code generation
    print("\n--- Generating EXPlora code... ---\n")
    code_snippet = generate_validated_code_from_plan(plan, context, documentation=documentation)
    print("\n--- Generated EXPlora code ---\n")
    print(code_snippet)
    code_snippet = "\n".join(code_snippet.split("\n")[1:-1])
    code = replace_first_ai_block(code, code_snippet)
    code = "\n".join(code.split("\n")[1:-1])
    print("\n--- Full EXPlora code with this snippet ---\n")
    print(code)

    ans = input("Would you like to change the code (y/n)? ")
    if ans == "y":
        edited_code = manual_edit_code(code)
        if edited_code is None:
            raise RuntimeError(
                f"No valid code and manual edit cancelled (run_id={run_id})."
            )
        code = edited_code

    return {"plan": plan, "code": code}


if __name__ == "__main__":
    user_request = "Read a CSV file, group by `category` column and calculate mean value by `value` column, then plot a bar chart"
    codegen_pipeline(user_request, "None", plan_check="manual", generator_name="GENERATOR_MODEL", judge_name="JUDGE_MODEL")