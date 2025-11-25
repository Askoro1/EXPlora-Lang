"""
plan_judge
==========

This module defines a simple judging mechanism for invalid execution
plans produced by the planner in the EXPlora-Lang toolchain.  When
`validate_plan_json` reports that a plan is not well‑formed, the
pipeline can invoke the judge to obtain constructive feedback.  The
feedback can then be passed back into the planner on subsequent
iterations via the `dev_notes` parameter, guiding the LLM to produce
a corrected plan.

The judge attempts to call the same underlying LLM provider used by
the planner (Google Gemini) if it is available and an API key has
been configured.  If the `google.genai` package or the `GEMINI_API_KEY`
environment variable is missing, the judge gracefully falls back to
returning a simple summary of the validation errors.  This fallback
ensures that the pipeline continues to function in test environments
without external LLM access.

Example usage:

    from .plan_judge import generate_judge_feedback

    feedback = generate_judge_feedback(plan_str, errors)
    new_plan = generate_plan(request, dev_notes=feedback)

The judge is deliberately separated from the planner to allow easy
extension or replacement with other models in the future.
"""

from __future__ import annotations

import os
import json
from typing import List

try:
    # Attempt to import the Gemini client.  This import may fail in
    # environments where the google APIs are not installed.  In such
    # cases the judge will fall back to a simple summariser.
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    _GOOGLE_AVAILABLE = True
except Exception:
    _GOOGLE_AVAILABLE = False


def _call_gemini_judge(plan_json: str, errors: List[str]) -> str:
    """Call the Gemini LLM to obtain feedback on an invalid plan.

    This helper constructs a system and user prompt that instructs the
    model to analyse the provided plan and validation errors.  It
    returns a plain‑text message describing what is wrong with the plan
    and how it should be corrected to satisfy the schema.  If the
    Gemini client cannot be initialised (e.g. API key missing) this
    function will raise an exception and the caller should fall back
    to a different strategy.

    Parameters
    ----------
    plan_json : str
        The JSON string representation of the invalid plan.
    errors : List[str]
        A list of human‑readable validation error messages produced by
        `validate_plan_json`.

    Returns
    -------
    str
        Feedback text to be presented to the planner.
    """
    api_key = os.environ.get("AIzaSyBrTLl0vgTDdslk4e0NP4169Y6JL54zi_0")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    # Initialise the client lazily to avoid import errors if google.genai
    # is unavailable at runtime.
    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.5-flash"

    system_prompt = (
        "You are an AI plan evaluator. Your task is to analyse a JSON\n"
        "execution plan and a list of schema validation errors, then\n"
        "provide clear and actionable feedback to the planner. Your\n"
        "feedback should explain what is wrong with the plan and suggest\n"
        "how to correct the issues so that the next plan will satisfy\n"
        "the required schema. Do not rewrite the entire plan or produce\n"
        "JSON; simply describe the needed changes in plain text."
    )
    user_prompt = (
        "Here is an execution plan and the validation errors it produced.\n\n"
        "Plan (as JSON):\n"
        f"{plan_json}\n\n"
        "Validation errors:\n"
        f"{os.linesep.join(errors)}\n\n"
        "Please list the problems with the plan and suggest how to fix them\n"
        "so that it conforms to the schema."
    )

    # Configure the model with a generic content type and a low temperature
    # to encourage deterministic feedback.  We do not specify a response
    # schema here since the expected output is free‑form text.
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.2,
        response_mime_type="text/plain",
    )

    response = client.models.generate_content(
        model=model_id,
        contents=user_prompt,
        config=config,
    )
    text_output = response.text.strip()
    return text_output


def generate_judge_feedback(plan_json: str, errors: List[str]) -> str:
    """Generate feedback for an invalid plan.

    This function first attempts to call an external LLM (Gemini) for
    feedback.  If that is not possible, it falls back to a simple
    heuristic that returns the validation errors as guidance.  The
    returned feedback can be passed into the `dev_notes` parameter of
    `generate_plan` to help the planner produce a corrected plan.

    Parameters
    ----------
    plan_json : str
        The JSON string representation of the invalid plan.
    errors : List[str]
        A list of validation error messages.

    Returns
    -------
    str
        Feedback for the planner.
    """
    if _GOOGLE_AVAILABLE:
        try:
            return _call_gemini_judge(plan_json, errors)
        except Exception:
            # On any failure (missing API key, client error, etc.) fall
            # back to the simple summariser.
            pass
    # Fallback: summarise the errors into a single string.  This still
    # conveys useful information to the planner even without an LLM.
    if not errors:
        return (
            "The plan failed validation but no errors were provided. Ensure the plan adheres to the required schema."
        )
    summary_lines = [
        "The plan you provided did not conform to the required schema.",
        "Here are the validation errors detected:",
    ]
    for err in errors:
        summary_lines.append(f" - {err}")
    summary_lines.append(
        "Please address these issues in your next plan. Make sure to provide all required fields, use the correct data types, "
        "and follow the schema's structure."
    )
    return os.linesep.join(summary_lines)