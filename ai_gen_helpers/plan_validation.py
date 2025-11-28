"""
Validation and logging utilities for EXPlora‑Lang execution plans.

This module provides helpers to validate JSON plans against the expected
schema, to allow manual correction of invalid plans, and to record plan
validation attempts in a log file.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

LOG_FILE: str = "plan_runs.jsonl"  # one JSON record per line


def validate_plan_json(plan_json: str) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """
    Parse ``plan_json`` and validate it against the plan schema.

    Parameters
    ----------
    plan_json : str
        A JSON string representation of a plan.

    Returns
    -------
    tuple
        ``(ok, errors, plan)`` where ``ok`` is a boolean indicating whether
        the plan is valid, ``errors`` is a list of human‑readable error
        messages, and ``plan`` is the parsed plan dictionary when valid or
        ``None`` when invalid.
    """
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], None
    ok, errors = validate_plan_dict(plan)
    return ok, errors, plan


def validate_plan_dict(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a plan dictionary according to the schema expected by the code
    generator.  The schema is reproduced here for easy reference:

    ``{
        "problem": string,
        "data_requirements": [
            { "name": string, "type": string, "description": string }, ...
        ],
        "steps": [
            { "id": int, "description": string, "dependencies": [int, ...] }, ...
        ],
        "notes": string
    }``

    Parameters
    ----------
    plan : dict
        The plan object to validate.

    Returns
    -------
    tuple
        ``(ok, errors)`` where ``ok`` is ``True`` if the plan is valid and
        ``errors`` is a list of error messages.  ``errors`` will be empty
        when ``ok`` is ``True``.
    """
    errors: List[str] = []
    # Top‑level object must be a dict
    if not isinstance(plan, dict):
        return False, ["Plan must be a JSON object."]
    # ``problem`` field
    problem = plan.get("problem")
    if not isinstance(problem, str) or not problem.strip():
        errors.append('"problem" must be a non‑empty string.')
    # ``data_requirements`` field
    data_reqs = plan.get("data_requirements")
    if not isinstance(data_reqs, list) or not data_reqs:
        errors.append('"data_requirements" must be a non‑empty list.')
    else:
        for idx, dr in enumerate(data_reqs):
            ctx = f"data_requirements[{idx}]"
            if not isinstance(dr, dict):
                errors.append(f"{ctx}: must be an object.")
                continue
            name = dr.get("name")
            dtype = dr.get("type")
            desc = dr.get("description")
            if not isinstance(name, str) or not name.strip():
                errors.append(f'{ctx}: "name" must be a non‑empty string.')
            if not isinstance(dtype, str) or not dtype.strip():
                errors.append(f'{ctx}: "type" must be a non‑empty string.')
            if not isinstance(desc, str) or not desc.strip():
                errors.append(f'{ctx}: "description" must be a non‑empty string.')
    # ``steps`` field
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append('"steps" must be a non‑empty list.')
        # Without steps nothing else makes sense, so return early
        return (len(errors) == 0), errors
    # Collect step ids
    ids: List[int] = []
    for idx, step in enumerate(steps):
        ctx = f"steps[{idx}]"
        if not isinstance(step, dict):
            errors.append(f"{ctx}: step must be an object.")
            continue
        sid = step.get("id")
        if not isinstance(sid, int):
            errors.append(f'{ctx}: "id" must be an integer.')
            continue
        if sid in ids:
            errors.append(f"{ctx}: duplicate id {sid}.")
        else:
            ids.append(sid)
    id_set = set(ids)
    # Validate descriptions and dependencies
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue  # already reported
        ctx = f"steps[{idx}]"
        sid = step.get("id")
        desc = step.get("description")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f'{ctx}: "description" must be a non‑empty string.')
        deps = step.get("dependencies")
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            errors.append(f'{ctx}: "dependencies" must be a list.')
            continue
        for d in deps:
            if not isinstance(d, int):
                errors.append(f'{ctx}: dependency {d!r} must be an integer id.')
                continue
            if d not in id_set:
                errors.append(f'{ctx}: dependency {d} does not match any step "id".')
            if sid is not None and d == sid:
                errors.append(f'{ctx}: step cannot depend on itself (id={sid}).')
    # ``notes`` field
    notes = plan.get("notes")
    if not isinstance(notes, str):
        errors.append('"notes" must be a string (can be empty).')
    return (len(errors) == 0), errors


def manual_edit(original_plan: str, errors: List[str]) -> Optional[str]:
    """
    Open a temporary file containing the invalid plan and error messages for
    manual editing.

    Parameters
    ----------
    original_plan : str
        The JSON plan string that failed validation.
    errors : list of str
        A list of validation error messages.  These will be prepended as
        comments at the end of the file to guide the user.

    Returns
    -------
    str or None
        The edited JSON plan string with comment lines stripped, or ``None``
        if the user cancelled editing.
    """
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