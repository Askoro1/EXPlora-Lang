from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import tempfile
import subprocess
import os
import json


LOG_FILE = "plan_runs.jsonl"  # one JSON per line


def validate_plan_json(plan_json: str) -> Tuple[bool, List[str], Dict[str, Any] | None]:
    """Parse JSON and then validate against the new plan schema."""
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], None

    ok, errors = validate_plan_dict(plan)
    return ok, errors, plan

def validate_plan_dict(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a plan object according to the new schema:

    {
        "problem": string,
        "data_requirements": [
            { "name": string, "type": string, "description": string }, ...
        ],
        "steps": [
            { "id": int, "description": string, "dependencies": [int, ...] }, ...
        ],
        "notes": string
    }
    """
    errors: List[str] = []

    # --- top-level checks ---
    if not isinstance(plan, dict):
        return False, ["Plan must be a JSON object."]

    # problem
    problem = plan.get("problem")
    if not isinstance(problem, str) or not problem.strip():
        errors.append('"problem" must be a non-empty string.')

    # data_requirements
    data_reqs = plan.get("data_requirements")
    if not isinstance(data_reqs, list) or not data_reqs:
        errors.append('"data_requirements" must be a non-empty list.')
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
                errors.append(f'{ctx}: "name" must be a non-empty string.')
            if not isinstance(dtype, str) or not dtype.strip():
                errors.append(f'{ctx}: "type" must be a non-empty string.')
            if not isinstance(desc, str) or not desc.strip():
                errors.append(f'{ctx}: "description" must be a non-empty string.')

    # steps
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append('"steps" must be a non-empty list.')
        # without steps nothing else makes sense
        return (len(errors) == 0), errors

    # first pass: collect ids
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

    # second pass: description + dependencies
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue  # already reported
        ctx = f"steps[{idx}]"
        sid = step.get("id")

        # description
        desc = step.get("description")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f'{ctx}: "description" must be a non-empty string.')

        # dependencies
        deps = step.get("dependencies")
        if deps is None:
            # allow missing -> treat as empty list
            deps = []
        if not isinstance(deps, list):
            errors.append(f'{ctx}: "dependencies" must be a list.')
            continue

        for d in deps:
            if not isinstance(d, int):
                errors.append(f'{ctx}: dependency {d!r} must be an integer id.')
                continue
            if d not in id_set:
                errors.append(
                    f'{ctx}: dependency {d} does not match any step "id".'
                )
            if sid is not None and d == sid:
                errors.append(f'{ctx}: step cannot depend on itself (id={sid}).')

    # notes
    notes = plan.get("notes")
    if not isinstance(notes, str):
        errors.append('"notes" must be a string (can be empty).')

    return (len(errors) == 0), errors

def manual_edit_plan(original_plan: Dict[str, Any], errors: list[str]) -> str | None:
    """
    Manual editing function.
    Opens a temp file, writes the errors and the plan in it.
    After the user modifies the plan, the temp file is closed and the new plan is validated.
    """

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

        # Write the original plan first
        json.dump(original_plan, tmp, indent=4)
        if len(errors) > 0:
            tmp.write("\n\n")
            tmp.write("// --- Validation errors (for your reference) ---\n")
            for e in errors:
                tmp.write(f"// {e}\n")

    # Use vim (or whatever EDITOR is set to)
    editor = os.environ.get("EDITOR") or "vim"
    subprocess.run([editor, tmp_path])

    # Read edited file
    with open(tmp_path, "r", encoding="utf-8") as f:
        edited = f.readlines()

    # Strip comment lines (starting with //) before returning to validator
    cleaned_lines = [
        line for line in edited
        if not line.lstrip().startswith("//")
    ]
    cleaned = "".join(cleaned_lines)

    return cleaned

def log_plan_attempt(run_id: str, attempt: int, validity: str, reason: str, plan_txt: str, mode: str, generator_name: str = "GENERATOR_NOT_SET", judge_name: str = "JUDGE_NOT_SET", ) -> None:
    """
    Logs the attempt with relevant information.
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

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry))
        f.write("\n")