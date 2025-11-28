"""
Judge helper for invalid EXPlora‑Lang plans.

Provides a thin wrapper around a Gemini model to critique invalid plans and
suggest improvements for the next planning attempt.  When the API is
unavailable, it simply returns the validation error messages.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore

# Use the same model as the planner by default.  This can be overridden by
# passing a different model identifier when calling judge_plan.
MODEL_ID: str = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API")
if genai is not None and API_KEY:
    _client: Optional[genai.Client] = genai.Client(api_key=API_KEY)  # type: ignore
else:
    _client = None


def judge_plan(plan_json: str, errors: str, user_request: str, *, model_id: str = MODEL_ID) -> str:
    """
    Ask an LLM to critique an invalid plan and return feedback to the planner.

    Parameters
    ----------
    plan_json : str
        The invalid plan as a JSON string.  This will be provided verbatim
        to the judge so it can inspect the structure and values.
    errors : str
        A semicolon‑separated string of validation error messages.  This is
        produced by the validator and summarises what went wrong.
    user_request : str
        The original natural language request from the user.  Including this
        helps the judge understand the intent behind the plan.
    model_id : str, optional
        Identifier of the Gemini model to use for judging.  Defaults to
        ``gemini-2.5-flash``.

    Returns
    -------
    str
        A piece of feedback instructing the planner how to improve the next
        attempt.  The feedback is intended to be appended to the planning
        prompt so that the LLM can avoid previous mistakes.
    """
    # If no API key is configured, simply return the error messages.  This
    # ensures the pipeline continues to function without network access.
    if _client is None:
        return errors
    system_prompt = (
        "You are an expert execution plan reviewer for EXPlora‑Lang.\n"
        "Your job is to read an invalid execution plan and a list of validation errors,\n"
        "and provide constructive feedback explaining how the plan can be improved to meet\n"
        "the required JSON schema.\n\n"
        "Guidelines:\n"
        "- Focus on the structural issues identified by the validator.\n"
        "- Suggest adding or correcting missing fields, data requirements or steps.\n"
        "- Do not rewrite the entire plan; instead, describe what is missing or incorrect.\n"
        "- Keep the feedback concise and actionable.\n"
    )
    user_prompt = (
        f"User request:\n{user_request}\n\n"
        f"Invalid plan:\n{plan_json}\n\n"
        f"Validation errors:\n{errors}\n\n"
        "Provide feedback to improve the plan:"
    )
    try:
        response = _client.models.generate_content(
            model=model_id,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
            ),
        )
        return response.text.strip()
    except Exception:
        # On any failure, fall back to returning the original error messages.
        return errors