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


def judge_plan(user_intent, plan):
    prompt = f"""
    You are an expert validator of execution plans.

    Your task:
    Check whether the EXECUTION PLAN correctly and completely matches the USER INTENT.

    You must evaluate:
    1. Whether all key requirements from the USER INTENT are present in the EXECUTION PLAN
    2. Whether the plan introduces anything NOT requested by the user
    3. Whether the interpretation of the user intent is correct and not distorted
    4. Whether anything important is missing, contradictory, or misunderstood

    You must be **strict and literal**.

    Your output must follow exactly this format:

    VERDICT: <one of: PASS | FAIL>

    CORRECTIONS/MISSING/UNWANTED (if there are ANY):
    - <what should be changed to make the plan correct 1>
    - <what should be changed to make the plan correct 2>
    - <...>

    Do NOT rewrite the whole plan.
    Do NOT generate code.
    Do NOT explain anything else.

    USER INTENT:
    {user_intent}

    EXECUTION PLAN:
    {plan}
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2
        )
    )

    return response.text.strip()


def codegen_pipeline(prompt_: str, code: str = "None", context_strategy: str = "None"):
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

    # Generate the plan
    print("\n--- Generating Plan... ---\n")
    plan = generate_plan(prompt_, context=context, documentation=documentation)
    plan_str = json.dumps(plan)
    print("[Generation Result]")
    print(plan_str)

    # Validate the plan
    verdict = judge_plan(prompt_, plan_str)
    print()
    print("[LLM-Judge Verdict]")
    print(verdict)
    print()

    # If there's a valid plan
    if "VERDICT: PASS" in verdict:
        print("\nPlan is valid.\n")

        ans = input("Would you like to check the plan (y/n)? ")
        if ans == "y":
            edited_plan = manual_edit_plan(plan, [])
            if edited_plan is None:
                raise RuntimeError(
                    f"No valid plan and manual edit cancelled (run_id={run_id})."
                )
            plan = edited_plan
    else:
        for _ in range(MAX_RETRIES):
            curr_attempt += 1
            print(f"[Attempt {curr_attempt}]")
            print()
            plan = generate_plan(prompt_, context=context, documentation=documentation, dev_notes="\n".join(verdict.split("\n")[1:]))
            plan_str = json.dumps(plan)
            print("[Generation Result]")
            print(plan_str)
            verdict = judge_plan(prompt_, plan_str)
            print()
            print("[LLM-Judge Verdict]")
            print(verdict)
            print()
            if "VERDICT: PASS" in verdict:
                print("\nPlan is valid.\n")

                ans = input("Would you like to check the plan (y/n)? ")
                if ans == "y":
                    edited_plan = manual_edit_plan(plan, [])
                    if edited_plan is None:
                        raise RuntimeError(
                            f"No valid plan and manual edit cancelled (run_id={run_id})."
                        )
                    plan = edited_plan

                break

        if "VERDICT: PASS" not in verdict:
            raise RuntimeError(f"Unable to generate valid plan after {MAX_RETRIES} attempts.")


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
    codegen_pipeline(user_request, "None")