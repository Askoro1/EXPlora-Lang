import os
import json
from typing import Dict, Any
from google import genai
from google.genai import types

from codegeneration.code_gen import generate_explora_code  # updated generator

# ---------------- CONFIG ---------------- #
GEMINI_MODEL = "gemini-2.0-flash"

# Read Gemini API key from environment
API_KEY = os.environ.get("GEMINI_API")
if not API_KEY:
    raise RuntimeError("Please set GEMINI_API_KEY environment variable.")

client = genai.Client(api_key=API_KEY)


# ---------------- VALIDATION ---------------- #
def validate_code(code: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    plan_json = json.dumps(plan, indent=2)

    with open("DOCUMENTATION.txt", "r", encoding="utf-8") as f:
        documentation = f.read()

    prompt = f"""
    You are an EXPlora-Lang validator.
    Check the following EXPlora-Lang program for the execution of the provided plan and correctness according to the official language rules.
    
    Return a JSON object exactly in this format:
    
    {{
      "valid": true/false,
      "errors": [
          {{"line": number, "message": "..."}}
      ]
    }}
    
    Do NOT rewrite the program. Only evaluate it.
    
    Documentation:
    {documentation}
    
    Plan:
    {plan_json}
    
    PROGRAM:
    {code}
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024
        )
    )

    text = response.text.strip()

    try:
        data = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        data = json.loads(text[start:end + 1])

    return data


# ---------------- REPAIR ---------------- #
def repair_code(code: str, validation_errors: Dict[str, Any]) -> str:
    """
    Repair EXPlora-Lang code using Gemini API based on validation errors.
    Returns only the corrected code (no explanations).
    """
    errors_json = json.dumps(validation_errors, indent=2)

    prompt = f"""
    You are an EXPlora-Lang expert.
    
    The following code contains errors:
    
    CODE:
    {code}
    
    ERRORS:
    {errors_json}
    
    Fix the code so it becomes valid EXPlora-Lang.
    Return ONLY the corrected EXPlora-Lang code. Do NOT provide any explanations.
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024
        )
    )

    corrected_code = response.text.strip()
    return corrected_code


# ---------------- MASTER PIPELINE ---------------- #
def generate_validated_code_from_plan(plan: Dict[str, Any], max_attempts: int = 3) -> str:
    """
    1. Generate EXPlora-Lang code from plan
    2. Validate with Gemini API
    3. Auto-repair if needed
    """
    code = generate_explora_code(plan)
    code = ""

    for attempt in range(max_attempts):
        result = validate_code(code, plan)

        if result.get("valid", False):
            print(f"[Validation] Code is valid on attempt {attempt + 1}")
            return code

        print(f"[Validation] Errors detected (attempt {attempt + 1}):")
        print(json.dumps(result, indent=2))

        # Repair code
        code = repair_code(code, result)

    raise RuntimeError(f"Unable to generate valid code after {max_attempts} attempts.")


# ---------------- EXAMPLE USAGE ---------------- #
if __name__ == "__main__":
    sample_plan = {
        "task": "Sum revenue by region and plot",
        "steps": [
            {"id": "s1", "action": "load_csv",
             "args": {"path": "sales.csv"},
             "produces": "df", "inputs": []},

            {"id": "s2", "action": "group_by",
             "args": {"by": ["region"]},
             "produces": "g", "inputs": ["df"]},

            {"id": "s3", "action": "aggregate",
             "args": {"metric": "sum", "column": "revenue"},
             "produces": "agg", "inputs": ["g"]},

            {"id": "s4", "action": "visualize",
             "args": {"type": "bar", "x": "region", "y": "revenue"},
             "produces": "chart", "inputs": ["agg"]}
        ],
        "outputs": [
            {"from": "chart", "type": "chart"}
        ]
    }

    final_code = generate_validated_code_from_plan(sample_plan)
    print("\n=== FINAL VALID EXPLORA-LANG CODE ===\n")
    print(final_code)
