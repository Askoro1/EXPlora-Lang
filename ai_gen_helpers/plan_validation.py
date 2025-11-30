from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

from .plan_gen import PLAN_SCHEMA as PLAN_STRUCTURE_SCHEMA

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "valid": {
            "type": "BOOLEAN",
        },
        "errors": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "message": {"type": "STRING"},
                },
                "required": ["message"],
            },
        },
    },
    "required": ["valid", "errors"],
}

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

GEMINI_MODEL: str = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API")
if genai is not None and API_KEY:
    _client = genai.Client(api_key=API_KEY)
else:
    _client = None

LOG_FILE: str = "plan_runs.jsonl"


def validate_plan_json(plan_json: str) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], None
    ok, errors = validate_plan_dict(plan)
    return ok, errors, plan


def validate_plan_dict(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(plan, dict):
        return False, ["Plan must be a JSON object."]

    # Use schema to check required fields and types
    properties = PLAN_STRUCTURE_SCHEMA.get("properties", {})
    required_keys = set(PLAN_STRUCTURE_SCHEMA.get("required", []))

    # Check for missing required keys
    for key in required_keys:
        if key not in plan or plan[key] in (None, ""):
            errors.append(f'"{key}" is missing or empty.')

    # Generic type checks based on schema definitions
    def _validate_value(value: Any, schema: Dict[str, Any], path: str) -> None:
        schema_type = schema.get("type")
        if schema_type == "STRING":
            # Special case: allow ``notes`` to be a list of strings as
            # described in the planning rules.  ``path`` contains the JSON
            # key with surrounding quotes (e.g., '"notes"'), so we can
            # inspect it directly.  If the value is a list and all items
            # are strings, treat it as valid.
            if path == '"notes"' and isinstance(value, list):
                if all(isinstance(n, str) for n in value):
                    return  # Accept list‑of‑string for notes
            if not isinstance(value, str) or (not value and path in required_keys):
                errors.append(f'{path} must be a non‑empty string.')
        elif schema_type == "INTEGER":
            if not isinstance(value, int):
                errors.append(f'{path} must be an integer.')
        elif schema_type == "ARRAY":
            if not isinstance(value, list):
                errors.append(f'{path} must be a list.')
            else:
                item_schema = schema.get("items")
                for i, item in enumerate(value):
                    _validate_value(item, item_schema, f'{path}[{i}]')
        elif schema_type == "OBJECT":
            if not isinstance(value, dict):
                errors.append(f'{path} must be an object.')
            else:
                sub_props = schema.get("properties", {})
                sub_required = schema.get("required", [])
                for rk in sub_required:
                    if rk not in value or value[rk] in (None, ""):
                        errors.append(f'{path}["{rk}"] is missing or empty.')
                for k, v in value.items():
                    if k in sub_props:
                        _validate_value(v, sub_props[k], f'{path}["{k}"]')
        else:
            # Unknown type in schema; silently accept
            return

    # Validate each property present in plan
    for key, value in plan.items():
        if key in properties:
            _validate_value(value, properties[key], f'"{key}"')

    # Additional semantic checks specific to steps
    steps = plan.get("steps")
    if isinstance(steps, list) and steps:
        ids: List[int] = []
        for idx, step in enumerate(steps):
            ctx = f'steps[{idx}]'
            # Ensure each step is a dict
            if not isinstance(step, dict):
                errors.append(f'{ctx} must be an object.')
                continue
            sid = step.get("id")
            if isinstance(sid, int):
                if sid in ids:
                    errors.append(f'{ctx}: duplicate id {sid}.')
                else:
                    ids.append(sid)
            # Validate dependencies
            deps = step.get("dependencies")
            if deps is None:
                deps = []
            if not isinstance(deps, list):
                errors.append(f'{ctx}: "dependencies" must be a list.')
            else:
                for d in deps:
                    if not isinstance(d, int):
                        errors.append(f'{ctx}: dependency {d!r} must be an integer id.')
                    elif d not in ids:
                        errors.append(f'{ctx}: dependency {d} does not match any step "id".')
                    elif sid is not None and d == sid:
                        errors.append(f'{ctx}: step cannot depend on itself (id={sid}).')

    return (len(errors) == 0), errors


def validate_plan(plan: Dict[str, Any], *, documentation: str = "None", model: str = GEMINI_MODEL) -> Dict[str, Any]:
    if _client is None or genai is None or types is None:
        ok, errors = validate_plan_dict(plan)
        return {
            "valid": ok,
            "errors": [{"message": e} for e in errors],
        }

    plan_json = json.dumps(plan, indent=4)
    schema_json = json.dumps(PLAN_STRUCTURE_SCHEMA, indent=4)
    prompt = f"""
You are an EXPlora‑Lang plan validator.
Check whether the following plan is valid according to the plan schema.  In
addition to structural correctness, ensure that required fields are
non‑empty and that step identifiers and dependencies are consistent.  If
the plan is invalid, list each reason concisely.

Return a JSON object exactly in this format:

{{
  "valid": true/false,
  "errors": [
    {{"message": "..."}},
    ...
  ]
}}

Plan schema:
{schema_json}

PLAN:
{plan_json}
"""
    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=PLAN_SCHEMA,
    )
    response = _client.models.generate_content(  # type: ignore[union-attr]
        model=model,
        contents=prompt,
        config=config,
    )
    text = response.text.strip()
    # Attempt to parse the response as JSON.  If it contains extra text
    # around the JSON, extract the first and last braces.
    try:
        data: Dict[str, Any] = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        data = json.loads(text[start : end + 1])
    # Ensure the errors list is always present
    if data.get("errors") is None:
        data["errors"] = []
    return data


def validate_plan_json_json(plan_json: str, *, documentation: str = "None", model: str = GEMINI_MODEL) -> Dict[str, Any]:
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [{"message": f"Invalid JSON: {e}"}],
        }
    return validate_plan(plan, documentation=documentation, model=model)


def manual_edit(original_plan: str, errors: List[str]) -> Optional[str]:
    print("Plan is invalid. Opening it for manual correction...")
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json", encoding="utf-8") as tmp:
        tmp_path = tmp.name
        # Write the original plan first
        tmp.write(original_plan)
        tmp.write("\n\n")
        tmp.write("// --- Validation errors (for your reference) ---\n")
        for e in errors:
            tmp.write(f"// {e}\n")
    # Use the user's configured editor or fall back to PyCharm
    editor = os.environ.get("EDITOR") or "pycharm64.exe"
    try:
        subprocess.run([editor, tmp_path])
    except Exception as e:
        print(f"Failed to launch editor '{editor}': {e}")
        return None
    # Read edited file
    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            edited = f.readlines()
    except FileNotFoundError:
        return None
    # Strip comment lines before returning to validator
    cleaned_lines = [line for line in edited if not line.lstrip().startswith("//")]
    cleaned = "".join(cleaned_lines)
    return cleaned


def log_plan_attempt(
    *,
    run_id: str,
    attempt: int,
    validity: str,
    reason: str,
    plan_txt: str,
    mode: str,
    generator_name: str = "GENERATOR_NOT_SET",
    judge_name: str = "JUDGE_NOT_SET",
) -> None:
    """
    Append a record of a planning attempt to ``LOG_FILE``.

    Each record includes timestamps and metadata about the planner and judge
    models.  The log file is written in newline‑delimited JSON (one entry per
    line).

    Parameters
    ----------
    run_id : str
        A unique identifier for the current pipeline run.
    attempt : int
        The ordinal attempt number.
    validity : str
        Either ``"valid"`` or ``"invalid"``.
    reason : str
        Description of why the plan is invalid or empty string when valid.
    plan_txt : str
        The raw JSON plan string.
    mode : str
        Either ``"MANUAL"`` or ``"LLM"`` depending on the validation mode.
    generator_name : str, optional
        Name or identifier of the generator model.
    judge_name : str, optional
        Name or identifier of the judge model.
    """
    entry = {
        "run_id": run_id,
        "attempt": attempt,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generator": generator_name,
        "judge": judge_name,
        "validity": validity,
        "reason": reason,
        "plan": plan_txt,
        "mode": mode,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry) + "\n")
    except Exception as e:
        # Logging failure should not halt the pipeline; print a warning
        print(f"Warning: failed to log plan attempt: {e}")