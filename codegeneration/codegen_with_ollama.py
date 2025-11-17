import json
from ollama import Client
from typing import Dict, Any

OLLAMA_MODEL = "llama3:latest"   # <-- your custom model name here


def generate_explora_code_with_ollama(plan: Dict[str, Any]) -> str:
    """
    Send the validated plan to the Ollama model and receive generated code.
    """

    client = Client()

    # Convert plan back to JSON so model can reason about it
    plan_json = json.dumps(plan, indent=2)

    with open("DOCUMENTATION.txt", "r", encoding="utf-8") as f:
        documen = f.read()

    prompt = f"""
    You are an EXPlora-Lang code generator.
    Convert the following validated execution plan into correct EXPlora-Lang code.
    Only output code. Do NOT explain anything.
    
    Explora-Lang Documentation:
    {documen}
    
    PLAN:
    {plan_json}
    """

    response = client.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        stream=False
    )

    return response["response"]
