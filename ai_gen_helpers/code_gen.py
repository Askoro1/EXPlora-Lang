"""
Code generation helper using Google Gemini.

Given a validated plan dictionary, this module uses a Gemini model to
translate the plan into EXPlora‑Lang code.  The caller must provide a
``GEMINI_API`` environment variable with a valid API key for the call to
succeed.  The model used can be configured via ``GEMINI_MODEL``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore

# Model configuration.  To switch to a different Gemini model, override this
# variable when calling ``generate_explora_code``.
GEMINI_MODEL: str = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API")
if genai is not None:
    if not API_KEY:
        raise RuntimeError(
            "Please set the environment variable GEMINI_API with your Gemini API key"
        )
    client = genai.Client(api_key=API_KEY)  # type: ignore
else:
    client = None  # type: ignore

def _read_documentation() -> str:
    """Read the EXPlora‑Lang documentation file relative to this module."""
    doc_path = os.path.join(os.path.dirname(__file__), "DOCUMENTATION.txt")
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_explora_code(plan: Dict[str, Any], *, model: str = GEMINI_MODEL) -> str:
    """
    Generate EXPlora‑Lang code from a validated execution plan using Gemini.

    Parameters
    ----------
    plan : dict
        The validated execution plan.  It must conform to the schema defined in
        ``plan_gen.PLAN_SCHEMA``.  ``plan`` will be serialized to JSON and
        included verbatim in the prompt.
    model : str, optional
        Identifier of the Gemini model to use.  Defaults to the module
        constant ``GEMINI_MODEL``.

    Returns
    -------
    str
        The generated EXPlora‑Lang code as a string with no explanatory text.
    """
    plan_json = json.dumps(plan, indent=4)
    documentation = _read_documentation()
    prompt = (
        "You are an EXPlora‑Lang code generator.\n"
        "Convert the following validated execution plan into correct EXPlora‑Lang code.\n"
        "Only output code. Do NOT explain anything.\n\n"
        "Explora‑Lang Documentation:\n"
        f"{documentation}\n\n"
        "PLAN:\n"
        f"{plan_json}\n"
    )
    if client is None or types is None:
        raise RuntimeError(
            "Google generative AI SDK is not installed; cannot generate code."
        )
    response = client.models.generate_content(  # type: ignore[union-attr]
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),  # type: ignore[index]
    )
    return response.text.strip()