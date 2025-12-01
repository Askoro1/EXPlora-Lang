import os
import json
from typing import Dict, Any
from google import genai
from google.genai import types
import tempfile
import subprocess

from .code_gen import generate_explora_code  # updated generator

# ---------------- CONFIG ---------------- #
GEMINI_MODEL = "gemini-2.5-flash"

# Read Gemini API key from environment
API_KEY = os.environ.get("GEMINI_API")
if not API_KEY:
    raise RuntimeError("Please set the environment variable GEMINI_API with your Gemini API key")

client = genai.Client(api_key=API_KEY)


# ---------------- VALIDATION ---------------- #
def validate_code(code: str, plan: Dict[str, Any], documentation="None") -> Dict[str, Any]:
    plan_json = json.dumps(plan, indent=4)

    prompt = f"""
    You are an EXPlora-Lang programming language validator.
    Check if the following EXPlora-Lang program represents the provided plan correctly, as well as if it follows the language rules and does NOT make any additional assumptions about them.
    
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
            temperature=0.2
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
def repair_code(code: str, validation_errors: Dict[str, Any], documentation="None") -> str:
    """
    Repair EXPlora-Lang code using Gemini API based on validation errors.
    Returns only the corrected code (no explanations).
    """
    errors_json = json.dumps(validation_errors, indent=4)

    prompt = f"""
    You are an EXPlora-Lang programming language expert.
    
    DOCUMENTATION:
    {documentation}
    
    The following code contains errors:
    
    CODE:
    {code}
    
    ERRORS:
    {errors_json}
    
    Fix the code so it becomes valid EXPlora-Lang code.
    Return ONLY the corrected EXPlora-Lang code. Do NOT provide any explanations.
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2
        )
    )

    corrected_code = response.text.strip()
    return corrected_code


def manual_edit_code(code: str) -> str:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tmp:
        tmp_path = tmp.name
        tmp.write(code)

    # Use vim (or whatever EDITOR is set to)
    editor = os.environ.get("EDITOR") or "vim"
    subprocess.run([editor, tmp_path])

    # Read edited file
    with open(tmp_path, "r", encoding="utf-8") as f:
        edited = f.read()

    return edited


# ---------------- MASTER PIPELINE ---------------- #
def generate_validated_code_from_plan(plan: Dict[str, Any], code: str, documentation="None", max_attempts: int = 3) -> str:
    """
    1. Generate EXPlora-Lang code from plan
    2. Validate with Gemini
    3. Auto-repair if needed
    """
    code_snippet = generate_explora_code(plan, code, documentation=documentation)

    print("[Generation Result]")
    print(code_snippet)

    for attempt in range(max_attempts):
        result = validate_code(code_snippet, plan, documentation=documentation)

        if result.get("valid", False):
            print(f"[Validation] Code is valid on attempt {attempt + 1}")
            return code_snippet

        print(f"[Validation] Errors detected (attempt {attempt + 1}):")
        print(json.dumps(result, indent=4))

        if attempt < max_attempts - 1:
            # Repair code
            code_snippet = repair_code(code_snippet, result, documentation=documentation)

        print()
        print("[Generation Result]")
        print(code_snippet)
        print()

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
