from ai_gen_helpers.plan_validation import validate_plan_json

invalid_plan_json = '{"problem": "", "data_requirements": [], "steps": [], "notes": ""}'
ok, errors, plan = validate_plan_json(invalid_plan_json)
print(ok)      # False
print(errors)  # тут будут сообщения валидатора