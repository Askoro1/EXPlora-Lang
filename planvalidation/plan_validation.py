import json
from typing import Any, Dict, List, Tuple

ALLOWED_ACTIONS = {"load_csv", "filter", "group_by", "aggregate", "visualize"}

def validate_plan_json(plan_json: str) -> Tuple[bool, List[str], Dict[str, Any] | None]:
    """Parse JSON and then validate."""
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], None

    ok, errors = validate_plan_dict(plan)
    return ok, errors, plan

def validate_plan_dict(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a plan object according to the PLSD_Plan_Validation.txt schema."""
    errors: List[str] = []

    # --- top-level checks ---
    if not isinstance(plan, dict):
        return False, ["Plan must be a JSON object."]

    if "task" not in plan:
        errors.append('Missing top-level "task" field.')

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append('"steps" must be a non-empty list.')
        return False, errors  # without steps nothing else makes sense

    outputs = plan.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append('"outputs" must be a non-empty list')

    # --- per-step checks ---
    seen_ids: set[str] = set()
    produced: set[str] = set()
    actions_so_far: List[str] = []

    for idx, step in enumerate(steps):
        ctx = f"step {idx}"
        if not isinstance(step, dict):
            errors.append(f"{ctx}: step must be an object")
            continue

        sid = step.get("id")
        action = step.get("action")
        args = step.get("args")
        inputs = step.get("inputs", [])
        produces_name = step.get("produces")

        # id
        if not isinstance(sid, str) or not sid:
            errors.append(f"{ctx}: missing or empty 'id'")
        elif sid in seen_ids:
            errors.append(f"{ctx}: duplicate id {sid!r}")
        else:
            seen_ids.add(sid)

        # action
        if action not in ALLOWED_ACTIONS:
            errors.append(f"{ctx}: invalid action {action!r}")
        actions_so_far.append(action)

        # args
        if not isinstance(args, dict):
            errors.append(f"{ctx}: 'args' must be an object")

        # inputs must be list of previously produced names
        if not isinstance(inputs, list):
            errors.append(f"{ctx}: 'inputs' must be a list")
            inputs = []
        for inp in inputs:
            if inp not in produced:
                errors.append(
                    f"{ctx}: input {inp!r} not produced by any previous step"
                )

        # produces
        if not isinstance(produces_name, str) or not produces_name:
            errors.append(f"{ctx}: missing or empty 'produces'")
        elif produces_name in produced:
            errors.append(f"{ctx}: duplicate produces name {produces_name!r}")
        else:
            produced.add(produces_name)

        # simple prerequisites
        if action == "aggregate" and "group_by" not in actions_so_far:
            errors.append(f"{ctx}: 'aggregate' requires a previous 'group_by' step")

        if action == "visualize" and not inputs:
            errors.append(f"{ctx}: 'visualize' must have at least one input")

    # --- outputs must refer to something produced ---
    if isinstance(outputs, list):
        for idx, out in enumerate(outputs):
            if not isinstance(out, dict):
                errors.append(f"output {idx}: must be an object")
                continue
            frm = out.get("from")
            if frm not in produced:
                errors.append(
                    f"output {idx}: 'from'={frm!r} not produced by any step"
                )

    return (len(errors) == 0), errors

# Example plan

# plan = {
#     "task": "Sum revenue by region and plot",
#     "steps": [
#         {"id": "s1", "action": "load_csv",
#          "args": {"path": "sales.csv"},
#          "produces": "df", "inputs": []},
#
#         {"id": "s2", "action": "group_by",
#          "args": {"by": ["region"]},
#          "produces": "g", "inputs": ["df"]},
#
#         {"id": "s3", "action": "aggregate",
#          "args": {"metric": "sum", "column": "revenue"},
#          "produces": "agg", "inputs": ["g"]},
#
#         {"id": "s4", "action": "visualize",
#          "args": {"type": "bar", "x": "region", "y": "revenue"},
#          "produces": "chart", "inputs": ["agg"]}
#     ],
#     "outputs": [
#         {"from": "chart", "type": "chart"}
#     ]
# }