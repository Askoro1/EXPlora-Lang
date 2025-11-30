import os
import json
from typing import Dict, Any
from google import genai
from google.genai import types

# ---------------- CONFIG ---------------- #
GEMINI_MODEL = "gemini-2.5-flash"   # or whatever Gemini model you want

API_KEY = os.environ.get("GEMINI_API")
if not API_KEY:
    raise RuntimeError("Please set the environment variable GEMINI_API with your Gemini API key")

client = genai.Client(api_key=API_KEY)

def generate_explora_code(plan: Dict[str, Any], documentation="None") -> str:
    """
    Send the validated plan to the Gemini API and receive generated EXPlora-Lang code.
    """

    plan_json = json.dumps(plan, indent=4)

    prompt = f"""
    You are an EXPlora-Lang programming language code generator.
    Convert the following validated execution plan into correct EXPlora-Lang code.
    Only output code (**it MUST be put between 3 BACKQUOTES before it and 3 after it**, like this: 
    ```
    code
    ```
    ).
    Do NOT explain anything.
    Try to write **less comments**. If you write comments, do it only for the most **important parts**.
    
    Explora‑Lang Documentation:
    {documentation}
    
    PLAN:
    {plan_json}
    """

    # Use the GenAI client to call Gemini
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2
        )
    )

    # response is a `GenerateContentResponse`
    # `parts` may be a list of content parts, but `.text` gives the full text
    return response.text.strip()


# ---------------- EXAMPLE USAGE ---------------- #

if __name__ == "__main__":
    plan = {
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

    code = generate_explora_code(plan)
    print("=== GENERATED EXPLORA‑LANG CODE ===\n", code)