"""
Plan generation helper for EXPlora‑Lang.

This module defines functions to construct a JSON execution plan using a
Gemini model.  The output must conform to a simple schema understood by
the rest of the pipeline.  When iterating on invalid plans, optional
``judge_feedback`` can be appended to the prompt to steer subsequent
generations.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:
    # If the Google generative AI SDK is not installed, assign stubs.  This
    # allows the module to be imported during testing without raising an
    # ImportError.  Any attempt to use these stubs at runtime will result
    # in a RuntimeError when ``generate_plan`` is called.
    genai = None  # type: ignore
    types = None  # type: ignore


MODEL_ID: str = "gemini-2.5-flash"

# Retrieve API key from environment.  Only construct a client when the SDK
# is available; otherwise leave ``client`` as ``None``.  A RuntimeError
# will be raised when ``generate_plan`` is called without a valid client.
API_KEY = os.environ.get("GEMINI_API")
if genai is not None:
    if not API_KEY:
        raise RuntimeError(
            "Please set the environment variable GEMINI_API with your Gemini API key"
        )
    client = genai.Client(api_key=API_KEY)  # type: ignore
else:
    client = None  # type: ignore

# Define the JSON schema for the plan.  The planner is instructed to conform
# to this schema when generating a plan.  See ``plan_validation.py`` for
# details about how the schema is enforced.
PLAN_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "problem": {
            "type": "STRING",
            "description": "A clear statement of the problem to be solved.",
        },
        "data_requirements": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "type": {"type": "STRING"},
                    "description": {"type": "STRING"},
                },
                "required": ["name", "type", "description"],
            },
            "description": "List of input data variables or files required.",
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
                        "description": "List of step IDs that must be completed before this step.",
                    },
                },
                "required": ["id", "description", "dependencies"],
            },
            "description": "Sequential list of execution steps.",
        },
        "notes": {
            "type": "STRING",
            "description": "Any additional context, assumptions, or limitations.",
        },
    },
    "required": ["problem", "data_requirements", "steps", "notes"],
}

# System prompt instructing the planner on how to behave.  It is deliberately
# verbose to provide enough context for the LLM to understand the task
SYSTEM_PROMPT: str = """
You are an AI planning engine (planner) for EXPlora‑Lang programming language.
Your goal is to analyze the user's request and the current execution context
to create a detailed structural plan.  You should **produce a JSON‑serializable
execution plan**, not actual code.

You should produce a detailed and technically sound execution plan.

Structure the output as valid JSON. Do NOT output non‑JSON outside the JSON object.

Here are the rules for the plan itself:
- Do not write code.
- Produce a structured reasoning plan describing how code SHOULD be written.
- The plan must be **explicit** and actionable enough that another model can
  later implement it into code.
- Be **concrete**, **technical**, and **avoid hand‑wavy theoretical descriptions**.
  Describe the steps **concisely**.

Here are the rules for the JSON:
1. The root must be a JSON object.
2. It should have the following top‑level keys:
   - `problem`: description of what to do (string).
   - `data_requirements`: list of required data or inputs (array of objects).
   - `steps`: a list of plan steps (array), each step is an object with:
       - `id`: unique identifier (integer).
       - `description`: what this step does (string).
       - `dependencies`: list of ids of steps that must come before (can be empty).
   - `notes`: optional extra notes (string or array), e.g. edge cases or assumptions.
3. Do NOT include any code snippets in the JSON, only plan in natural language
   (in the description fields).
4. The JSON must be well‑formed (parsable).
"""

USER_PROMPT_TEMPLATE: str = """
Generate an execution plan in JSON for the following user request in EXPlora‑Lang:

User request:
---
{REQUEST}
---

Context:
- Current function context (AST or code):
{CURRENT_FUNCTION_CONTEXT}

- Full program context (AST or code):
{PROGRAM_CONTEXT}

- EXPlora Documentation:
{DOCUMENTATION}

- Additional notes (e.g. libraries, constraints, types):
{DEVELOPER_NOTES}

{JUDGE_FEEDBACK_BLOCK}

Please output the plan as a JSON object conforming to the structure described in the system prompt.
"""

# Attempt to read the project documentation.  If the file does not exist, fall
# back to an empty string.  This makes the module usable even when the
# repository layout differs from the original upstream project.
_doc_path = os.path.join(os.path.dirname(__file__), "DOCUMENTATION.txt")
try:
    with open(_doc_path, "r", encoding="utf-8") as documentation_file:
        DOCUMENTATION: str = documentation_file.read()
except FileNotFoundError:
    DOCUMENTATION = ""


def generate_plan(
    request: str,
    *,
    current_func_context: str = "None",
    program_context: str = "None",
    documentation: str = DOCUMENTATION,
    dev_notes: str = "None",
    judge_feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a structured execution plan for EXPlora‑Lang using Gemini.

    Parameters
    ----------
    request : str
        Natural language description of the task to solve.
    current_func_context : str, optional
        String representation of the current function context (default "None").
    program_context : str, optional
        String representation of the full program context (default "None").
    documentation : str, optional
        EXPlora‑Lang documentation to provide to the planner.  Defaults to
        whatever is found in ``DOCUMENTATION.txt``.
    dev_notes : str, optional
        Additional developer notes, such as library requirements or constraints.
    judge_feedback : str or None, optional
        Feedback from a judge LLM describing why a previous plan was invalid.
        When provided, this feedback is appended to the user prompt to guide
        the planner away from previous mistakes.

    Returns
    -------
    dict
        The parsed JSON plan as a Python dictionary.

    Raises
    ------
    ValueError
        If the LLM returns a response that cannot be parsed as JSON.
    """

    # Build the user prompt.  Include a judge feedback block if feedback is
    # available; otherwise leave it empty.  The braces in the format string
    # must be doubled to escape them when used inside another format.
    if judge_feedback:
        judge_feedback_block = (
            "- Judge feedback from previous attempt:\n" + judge_feedback + "\n"
        )
    else:
        judge_feedback_block = ""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        REQUEST=request,
        CURRENT_FUNCTION_CONTEXT=current_func_context,
        PROGRAM_CONTEXT=program_context,
        DOCUMENTATION=documentation,
        DEVELOPER_NOTES=dev_notes,
        JUDGE_FEEDBACK_BLOCK=judge_feedback_block,
    )

    # Configure the Gemini generation call.  Low temperature helps produce
    # deterministic, schema‑adhering plans.  We also supply the plan schema
    # directly via response_schema so the LLM knows what to output.
    # If the SDK is unavailable, bail out early.  Tests patch this function,
    # so this branch is not reached during unit testing.
    if client is None or types is None:
        raise RuntimeError(
            "Google generative AI SDK is not installed; cannot generate plans."
        )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=PLAN_SCHEMA,
    )
    response = client.models.generate_content(  # type: ignore[union-attr]
        model=MODEL_ID,
        contents=user_prompt,
        config=config,
    )
    text_output = response.text
    try:
        plan_: Dict[str, Any] = json.loads(text_output)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse JSON from LLM output: {e}\nLLM output: {text_output}"
        )
    return plan_


if __name__ == "__main__":
    # Simple example usage when running this module directly.
    example_request = "Read a CSV file, group by `category` column and calculate the mean value of the `value` column, then plot a bar chart"
    plan = generate_plan(
        request=example_request,
        current_func_context="None",
        program_context="None",
        documentation=DOCUMENTATION,
    )
    print(json.dumps(plan, indent=2, ensure_ascii=False))