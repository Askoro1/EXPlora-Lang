import json

from .planvalidation import candidate_pipeline as cp  # type: ignore


def main() -> None:
    """
    Real end-to-end test of the EXPlora pipeline using Gemini:

    - LLM planner (generate_plan)
    - JSON schema validation
    - LLM judge feedback and auto-retry (if needed)
    - LLM code generation (generate_explora_code)

    This script assumes that:
    - google-genai is installed,
    - GEMINI_API is set in the environment,
    - plan_gen, plan_judge and code_gen are configured to use Gemini.
    """

    # You can change this request to anything you like.
    prompt = (
        "Write an EXPlora-lang program that declares an array of 5 integers, "
        "computes their sum in a loop, and returns the sum from main()."
    )

    # For now we use an empty context; the pipeline only needs a stringifiable object.
    context = {}

    result = cp.run_pipeline(
        prompt=prompt,
        context=context,
        manual_check=False,          # use the LLM judge auto-retry path
        generator_name="GEMINI_PLANNER",
        judge_name="GEMINI_JUDGE",
    )

    print("\n=== Final structured plan ===")
    print(json.dumps(result["plan"], indent=2, ensure_ascii=False))

    print("\n=== Final generated EXPlora code ===")
    print(result["code"])


if __name__ == "__main__":
    main()
