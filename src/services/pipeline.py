from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from domain.models import RAGResponse, RetrievedChunk
from ports.llm import LLMClient
from services.retriever import Retriever

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente de soporte para una empresa SaaS. "
    "Respondés preguntas de empleados basándote exclusivamente en la "
    "documentación interna provista como contexto. Reglas:\n"
    "1. Si la respuesta está en el contexto, respondé con detalle citando la fuente.\n"
    "2. Si el contexto no es suficiente, decí explícitamente que no tenés esa información.\n"
    "3. No inventes datos que no estén en el contexto."
)

_USER_TEMPLATE = (
    "## Pregunta\n{question}\n\n"
    "## Contexto recuperado\n{context}\n\n"
    "## Instrucciones\n"
    "Respondé solo con la información del contexto. "
    "Citá la fuente entre paréntesis al final de cada afirmación clave."
)


class RAGPipeline:
    """Retrieval-augmented generation for one knowledge domain.

    `system_prompt` is parameterized (not hardcoded) so the same class backs
    every specialized agent (HR/Tech/Finance) with only the prompt, data and
    vector collection changing between them — see src/agents/*.

    The generation step is a real LCEL chain (ChatPromptTemplate | chat_model
    | StrOutputParser), not a hand-built message list — this is the
    LangChain "chain" component the assignment asks for, and it's what
    Langfuse's callback handler traces as a single generation span.

    Moderation is NOT checked here — it's the Orchestrator's job as the
    system's single entry point (see ADR-007). This pipeline assumes its
    input already passed that gate.
    """

    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._retriever = retriever
        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", _USER_TEMPLATE)]
        )
        self._chain = prompt | llm.model | StrOutputParser()

    def ask(self, question: str, callbacks: list | None = None) -> RAGResponse:
        retrieved = self._retriever.retrieve(question)
        config = {"callbacks": callbacks} if callbacks else None
        answer = self._chain.invoke(
            {
                "question": question,
                "context": self._format_context(retrieved),
            },
            config=config,
        )
        return RAGResponse(
            user_question=question,
            system_answer=answer,
            chunks_related=retrieved,
        )

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
