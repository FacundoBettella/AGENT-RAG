"""Script 02 — Consulta al sistema FAQ.

Acepta una pregunta, recupera chunks relevantes y genera una respuesta.
Devuelve JSON estructurado con user_question, system_answer y chunks_related.

Uso:
    python scripts/02_query.py
    python scripts/02_query.py "¿Cómo solicito vacaciones?"
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from domain.exceptions import ContentBlockedError
from factory import build_faq_bundle

DEFAULT_QUESTION = "¿Cómo solicito vacaciones?"


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION

    bundle = build_faq_bundle()

    if bundle.indexer._store.count() == 0:
        print("ChromaDB está vacío. Ejecutá primero: python scripts/01_ingest.py")
        return

    print(f"Pregunta: {question}\n")
    try:
        response = bundle.pipeline.ask(question)
        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    except ContentBlockedError as e:
        print(json.dumps({"error": "contenido_bloqueado", "detalle": e.reason}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
