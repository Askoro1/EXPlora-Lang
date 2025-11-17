from planvalidation.plan_validation import validate_plan_json
from codegen_with_ollama import generate_explora_code_with_ollama

plan_json = """
{
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
"""

ok, errors, plan = validate_plan_json(plan_json)

if not ok:
    print("Validation errors:", errors)
else:
    code = generate_explora_code_with_ollama(plan)
    print("Generated EXPlora-Lang code:\n")
    print(code)