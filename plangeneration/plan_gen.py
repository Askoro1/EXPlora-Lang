import os
import json
from google import genai
from google.genai import types

MODEL_ID = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

PLAN_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "problem": {
            "type": "STRING",
            "description": "A clear statement of the problem to be solved."
        },
        "data_requirements": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "type": {"type": "STRING"},
                    "description": {"type": "STRING"}
                },
                "required": ["name", "type", "description"]
            },
            "description": "List of input data variables or files required."
        },
        "steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "INTEGER"},
                    "description": {"type": "STRING"},
                    "dependencies": {
                        "type": "ARRAY",
                        "items": {"type": "INTEGER"},
                        "description": "List of step IDs that must be completed before this step."
                    }
                },
                "required": ["id", "description", "dependencies"]
            },
            "description": "Sequential list of execution steps."
        },
        "notes": {
            "type": "STRING",
            "description": "Any additional context, assumptions, or limitations."
        }
    },
    "required": ["problem", "data_requirements", "steps", "notes"]
}

SYSTEM_PROMPT = """
You are an AI planning engine (planner) for EXPlora-lang programming language.  
Your goal is to analyze the user's request and the current execution context to create a detailed structural plan.
Your should **produce a JSON-serializable execution plan**, not actual code.  
You should produce a detailed and technically sound execution plan.

Structure the output as valid JSON. Do NOT output non-JSON outside the JSON object.
Your output must strictly follow the JSON schema provided.

Here are the rules for the plan itself:
- Do not write code.
- Produce a structured reasoning plan describing how code SHOULD be written.
- The plan must be **explicit** and actionable enough that another model can later implement it into code.
- Be **concrete**, **technical**, and **avoid hand-wavy theoretical descriptions**. Describe the steps **concisely**.

Here are the rules for the JSON:

1. The root must be a JSON object.  

2. It should have the following top-level keys:
   - `problem`: description of what to do (string).  
   - `data_requirements`: list of required data or inputs (array of objects).  
   - `steps`: a list of plan steps (array), each step is an object with:
     - `id`: unique identifier (integer).  
     - `description`: what this step does (string).  
     - `dependencies`: list of ids of steps that must come before (can be empty).  
   - `notes`: optional extra notes (string or array), e.g. edge cases or assumptions.

3. Do NOT include any code snippets in the JSON, only plan in natural language (in the description fields).

4. The JSON must be well-formed (parsable).
"""


USER_PROMPT = """
Generate an execution plan in JSON for the following user request in EXPlora-lang:

User request:
---
{REQUEST}
---

Context:
- Current function context (AST or code):  
{CURRENT_FUNCTION_CONTEXT}

- Full program context (AST or code):  
{PROGRAM_CONTEXT}

- EXPLora Documentation:
{DOCUMENTATION}

- Additional notes (e.g. libraries, constraints, types):  
{DEVELOPER_NOTES}

Please output the plan as a JSON object conforming to the structure described in the system prompt.
"""

with open("./EXPlora-Lang/DOCUMENTATION.txt", "r") as documentation_file:
    DOCUMENTATION = documentation_file.read()


def generate_plan(request: str,
                  current_func_context: str = "None",
                  program_context: str = "None",
                  documentation: str = "None",
                  dev_notes: str = "None") -> dict:

    user_prompt = USER_PROMPT.format(
        REQUEST=request,
        CURRENT_FUNCTION_CONTEXT=current_func_context,
        PROGRAM_CONTEXT=program_context,
        DOCUMENTATION=documentation,
        DEVELOPER_NOTES=dev_notes,
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2, # low temperature for "stricter" planning
        response_mime_type="application/json",
        response_schema=PLAN_SCHEMA
    )

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=user_prompt,
        config=config
    )

    text_output = response.text

    try:
        plan_ = json.loads(text_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON from LLM output: {e}\n LLM output: {text_output}")

    return plan_


if __name__ == "__main__":
    user_request = "Read a CSV file, group by `category` column and calculate mean value by `value` column, then plot a bar chart"
    plan = generate_plan(
        request=user_request,
        documentation=DOCUMENTATION,
        #dev_notes="use pandas and matplotlib"
    )
    with open('./EXPlora-Lang/plan.json', 'w') as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)
