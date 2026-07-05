from m2project.domain.exceptions import ContentBlockedError
from m2project.domain.moderation import ModerationAction
from m2project.domain.models import RAGResponse, RetrievedChunk
from m2project.ports.llm import LLMClient
from m2project.services.moderation_service import ModerationService
from m2project.services.retriever import Retriever

_SYSTEM_PROMPT = (
    "Eres un asistente de soporte para una empresa de HR SaaS. "
    "Respondés preguntas de empleados basándote exclusivamente en la "
    "documentación interna provista como contexto. Reglas:\n"
    "1. Si la respuesta está en el contexto, respondé con detalle citando la fuente.\n"
    "2. Si el contexto no es suficiente, decí explícitamente que no tenés esa información.\n"
    "3. No inventes datos que no estén en el contexto."
)


class RAGPipeline:
    def __init__(self, retriever: Retriever, llm: LLMClient, moderation: ModerationService) -> None:
        self._retriever = retriever
        self._llm = llm
        self._moderation = moderation

    def ask(self, question: str) -> RAGResponse:
        risks, action, reason = self._moderation.check(question)

        if action == ModerationAction.BLOCK:
            raise ContentBlockedError(reason)

        retrieved = self._retriever.retrieve(question)
        messages = self._build_messages(question, retrieved)
        answer = self._llm.chat(messages)
        return RAGResponse(
            user_question=question,
            system_answer=answer,
            chunks_related=retrieved,
        )

    def _build_messages(self, question: str, retrieved: list[RetrievedChunk]) -> list[dict]:
        context = self._format_context(retrieved)
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Pregunta\n{question}\n\n"
                    f"## Contexto recuperado\n{context}\n\n"
                    "## Instrucciones\n"
                    "Respondé solo con la información del contexto. "
                    "Citá la fuente entre paréntesis al final de cada afirmación clave."
                ),
            },
        ]

    @staticmethod
    def _format_context(retrieved: list[RetrievedChunk]) -> str:
        if not retrieved:
            return "(sin contexto disponible)"
        blocks = []
        for i, rc in enumerate(retrieved, start=1):
            source = rc.chunk.metadata.get("source", rc.chunk.document_id)
            blocks.append(
                f"[Fragmento {i} · fuente: {source} · similitud: {rc.similarity:.2f}]\n"
                f"{rc.chunk.content}"
            )
        return "\n\n".join(blocks)
