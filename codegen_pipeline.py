"""
Pipeline for generating EXPlora‑Lang code from a natural language prompt.

The ``codegen_pipeline`` function orchestrates plan generation, validation
with optional manual correction, automatic critique via a judge model, and
finally code generation.  Feedback from the judge can be passed back to
the planner on subsequent attempts.

This module relies on the ``GEMINI_API`` environment variable to access
Gemini models for plan and code generation.  If the variable is unset the
pipeline will raise a runtime error when invoked.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from .ai_gen_helpers.plan_gen import generate_plan
from .ai_gen_helpers.plan_validation import (
    validate_plan_json,
    manual_edit,
    log_plan_attempt,
)
from .ai_gen_helpers.code_gen import generate_explora_code
from .ai_gen_helpers.judge import judge_plan

# Allow up to this many retries when automatically regenerating a plan.
MAX_RETRIES: int = 10


def codegen_pipeline(
    prompt: str,
    context: Any,
    manual_check: bool = True,
    *,
    generator_name: str = "GENERATOR_MODEL",
    judge_name: str = "JUDGE_MODEL",
) -> Dict[str, Any]:
    """
    Generate EXPlora‑Lang code from a natural language ``prompt``.

    Parameters
    ----------
    prompt : str
        A natural language description of the task to perform.
    context : Any
        The current execution context (AST or source code).  This will be
        converted to a string and provided to the planner as part of its
        context.  If no context is available, pass ``None``.
    manual_check : bool, optional
        If ``True`` (default), invalid plans will be opened for manual editing
        using the user's preferred editor.  If ``False``, invalid plans will
        trigger an automatic loop where a judge LLM provides feedback to
        improve the next planning attempt.
    generator_name : str, optional
        An identifier for the generator LLM used for logging.  Default is
        ``"GENERATOR_MODEL"``.
    judge_name : str, optional
        An identifier for the judge LLM used for logging.  Default is
        ``"JUDGE_MODEL"``.

    Returns
    -------
    dict
        A dictionary with two keys:

        * ``"plan"`` – the validated plan as a Python ``dict``.
        * ``"code"`` – the EXPlora‑Lang code as a string.

    Raises
    ------
    RuntimeError
        If no valid plan could be produced after ``MAX_RETRIES`` attempts.
    """

    run_id: str = str(uuid.uuid4())
    judge_feedback: Optional[str] = None

    # Prepare string representations of the context once up front to avoid
    # repeating conversions inside the loop.
    context_str = "" if context is None else str(context)

    for attempt in range(1, MAX_RETRIES + 1):
        # Step 1: Generate a plan.  Pass any judge feedback from previous
        # invalid attempt so the planner can incorporate it.
        plan_dict = generate_plan(
            prompt,
            current_func_context=context_str,
            program_context=context_str,
            judge_feedback=judge_feedback,
        )
        plan_str = json.dumps(plan_dict)

        # Step 2: Validate the plan
        ok, errors, plan_result = validate_plan_json(plan_str)
        mode = "MANUAL" if manual_check else "LLM"

        if ok and plan_result is not None:
            # Successful plan
            log_plan_attempt(
                run_id=run_id,
                attempt=attempt,
                validity="valid",
                reason="",
                plan_txt=plan_str,
                mode=mode,
                generator_name=generator_name,
                judge_name=judge_name,
            )
            # Generate code based on the valid plan
            code = generate_explora_code(plan_result)
            return {"plan": plan_result, "code": code}

        # If we reach here, the plan was invalid
        error_msg = "; ".join(errors or ["unknown validation error"])

        if manual_check:
            # In manual mode, allow the user to iteratively fix the plan until
            # it passes validation or the user cancels.
            while True:
                log_plan_attempt(
                    run_id=run_id,
                    attempt=attempt,
                    validity="invalid",
                    reason=error_msg,
                    plan_txt=plan_str,
                    mode=mode,
                    generator_name=generator_name,
                    judge_name=judge_name,
                )
                print("Plan was invalid : Manual Check.")
                edited_plan = manual_edit(plan_str, errors or [])
                if edited_plan is None:
                    raise RuntimeError(
                        f"No valid plan and manual edit cancelled (run_id={run_id})."
                    )
                ok2, errors2, plan_result2 = validate_plan_json(edited_plan)
                if ok2 and plan_result2 is not None:
                    log_plan_attempt(
                        run_id=run_id,
                        attempt=attempt,
                        validity="valid",
                        reason="manual correction",
                        plan_txt=edited_plan,
                        mode=mode,
                        generator_name=generator_name,
                        judge_name=judge_name,
                    )
                    code = generate_explora_code(plan_result2)
                    return {"plan": plan_result2, "code": code}
                # otherwise update state and loop again
                error_msg = "; ".join(errors2 or ["unknown validation error"])
                errors = errors2[:]
                plan_str = edited_plan
        else:
            # In automatic mode, call the judge LLM to get feedback that will be
            # fed back into the next planning iteration.
            log_plan_attempt(
                run_id=run_id,
                attempt=attempt,
                validity="invalid",
                reason=error_msg,
                plan_txt=plan_str,
                mode=mode,
                generator_name=generator_name,
                judge_name=judge_name,
            )
            print("Plan was invalid : LLM Check.")
            try:
                # Ask the judge to critique the invalid plan.  We include the
                # original prompt for additional context so the judge can
                # recommend how to improve the plan.
                judge_feedback = judge_plan(
                    plan_str,
                    error_msg,
                    prompt,
                )
            except Exception as exc:
                # If the judge fails for any reason, fall back to using the
                # error message itself as feedback.  This ensures that the
                # planner will at least be informed of what went wrong.
                print(f"Judge call failed: {exc}. Falling back to error message.")
                judge_feedback = error_msg
            # continue to next iteration; judge_feedback will be passed to generate_plan
            continue

    # If loop completes without returning, no valid plan was found
    raise RuntimeError(
        f"No valid plan found after {MAX_RETRIES} attempts (run_id={run_id})."
    )


if __name__ == "__main__":
    # Basic manual test harness.  When run as a script, this will prompt the
    # user for a request and execute the pipeline in manual mode.  It is
    # primarily intended for debugging rather than production use.
    example_request = (
        "Read a CSV file, group by `category` column and calculate the mean value "
        "of the `value` column, then plot a bar chart."
    )
    res = codegen_pipeline(example_request, context=None, manual_check=True)
    print("\n--- Plan ---\n", json.dumps(res["plan"], indent=2))
    print("\n--- Code ---\n", res["code"])