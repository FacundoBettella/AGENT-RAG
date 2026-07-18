"""Script 03 — Evaluador de calidad de respuestas (LLM-as-judge).

Envía la pregunta al orquestador y evalúa la respuesta del agente elegido
con un LLM juez (services/evaluator.py — misma lógica que usa /api/evaluate
y, en el bonus, el evaluador integrado con la Score API de Langfuse).

Uso:
    python scripts/03_evaluate.py
    python scripts/03_evaluate.py "¿Cómo solicito vacaciones?"
"""

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adapters.openai_llm import OpenAILLMClient
from agents.orchestrator import build_orchestrator
from services.evaluator import evaluate_response

DEFAULT_QUESTION = "¿Cómo solicito vacaciones?"


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    orchestrator = build_orchestrator()
    evaluator_llm = OpenAILLMClient(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

    print(f"Pregunta: {question}\n")
    result = orchestrator.handle(question)

    print(f"=== Respuesta (intent={result.intent}) ===")
    print(json.dumps(result.rag_response.to_dict(), ensure_ascii=False, indent=2))

    print("\n=== Evaluación ===")
    evaluation = evaluate_response(evaluator_llm, result.rag_response)
    print(json.dumps(evaluation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
