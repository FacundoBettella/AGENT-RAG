"""LLM-as-judge evaluator: scores a RAG response's quality (1-10) given the
original question, the retrieved chunks and the generated answer.

Used by /api/evaluate directly, and by the Langfuse-integrated evaluator
(bonus) which pushes this same score through the Langfuse Score API instead
of just returning it in an HTTP response.
"""

from __future__ import annotations

import json

from domain.models import RAGResponse
from ports.llm import LLMClient

EVALUATOR_PROMPT = """Eres un evaluador experto de sistemas RAG.
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


def evaluate_response(llm: LLMClient, response: RAGResponse) -> dict:
    chunks_text = "\n\n".join(
        f"[Fragmento {i + 1} · similitud: {rc.similarity:.2f}]\n{rc.chunk.content}"
        for i, rc in enumerate(response.chunks_related)
    )
    messages = [
        {"role": "system", "content": EVALUATOR_PROMPT},
        {
            "role": "user",
            "content": (
                f"## Pregunta\n{response.user_question}\n\n"
                f"## Fragmentos recuperados\n{chunks_text}\n\n"
                f"## Respuesta generada\n{response.system_answer}"
            ),
        },
    ]
    raw = llm.chat(messages)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "No se pudo parsear la evaluación", "raw": raw}
