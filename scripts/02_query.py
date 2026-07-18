"""Script 02 — Consulta al sistema multi-agente.

Envía la pregunta al orquestador, que clasifica la intención y enruta al
agente RAG especializado correspondiente (HR/Tech/Finance). Devuelve JSON
estructurado con user_question, system_answer, chunks_related, intent y
reasoning (la justificación de la clasificación, útil para depurar
misclassifications).

Uso:
    python scripts/02_query.py
    python scripts/02_query.py "¿Cómo solicito vacaciones?"
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.orchestrator import build_orchestrator
from domain.exceptions import ContentBlockedError

DEFAULT_QUESTION = "¿Cómo solicito vacaciones?"


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    orchestrator = build_orchestrator()

    print(f"Pregunta: {question}\n")
    try:
        result = orchestrator.handle(question)
        output = result.rag_response.to_dict()
        output["intent"] = result.intent
        output["reasoning"] = result.reasoning
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except ContentBlockedError as e:
        print(json.dumps({"error": "contenido_bloqueado", "detalle": e.reason}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
