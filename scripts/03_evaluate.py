"""Script 03 — Evaluador de calidad de respuestas RAG.

Hace una pregunta al sistema y evalúa la calidad de la respuesta
usando un LLM como juez (LLM-as-judge).

Devuelve el RAGResponse original + un puntaje 0-10 con justificación.

Uso:
    python scripts/03_evaluate.py
    python scripts/03_evaluate.py "¿Cómo solicito vacaciones?"
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m2project.factory import build_faq_bundle

DEFAULT_QUESTION = "¿Cómo solicito vacaciones?"

_EVALUATOR_PROMPT = """Eres un evaluador experto de sistemas RAG.
Recibirás una pregunta, los fragmentos recuperados y la respuesta generada.
Evaluá la calidad de la respuesta con un puntaje de 0 a 10 según estos criterios:

- Relevancia (0-4): ¿los fragmentos recuperados son relevantes para la pregunta?
- Precisión (0-3): ¿la respuesta se basa en los fragmentos sin inventar información?
- Completitud (0-3): ¿la respuesta cubre todo lo que preguntaba el usuario?

Respondé ÚNICAMENTE con este JSON:
{
  "score": <número del 0 al 10>,
  "relevancia": <número del 0 al 4>,
  "precision": <número del 0 al 3>,
  "completitud": <número del 0 al 3>,
  "justificacion": "<una oración explicando el puntaje>"
}"""


def evaluate(bundle, response) -> dict:
    chunks_text = "\n\n".join(
        f"[Fragmento {i+1} · similitud: {rc.similarity:.2f}]\n{rc.chunk.content}"
        for i, rc in enumerate(response.chunks_related)
    )
    messages = [
        {"role": "system", "content": _EVALUATOR_PROMPT},
        {
            "role": "user",
            "content": (
                f"## Pregunta\n{response.user_question}\n\n"
                f"## Fragmentos recuperados\n{chunks_text}\n\n"
                f"## Respuesta generada\n{response.system_answer}"
            ),
        },
    ]
    raw = bundle.pipeline._llm.chat(messages)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "No se pudo parsear la evaluación", "raw": raw}


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION

    bundle = build_faq_bundle()

    if bundle.indexer._store.count() == 0:
        print("ChromaDB está vacío. Ejecutá primero: python scripts/01_ingest.py")
        return

    print(f"Pregunta: {question}\n")
    response = bundle.pipeline.ask(question)

    print("=== Respuesta ===")
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))

    print("\n=== Evaluación ===")
    evaluation = evaluate(bundle, response)
    print(json.dumps(evaluation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
