"""Orchestrator: classifies user intent and conditionally routes to the
specialized RAG agent for that domain.

Single entry point for the whole system. Order of operations per question:

1. Moderation gate — before any LLM call, so blocked content never reaches
   classification or a domain agent (see ADR-007: this is the only
   moderation check in the system, not duplicated inside each RAGPipeline).
2. Intent classification via structured output (hr/tech/finance/unknown,
   see ADR-006 for why structured output over free text/embeddings/keywords).
3. Conditional routing — dispatch to the matching domain agent, or return a
   graceful "out of scope" response for 'unknown' instead of forcing a bad
   answer out of one of the 3 domains.

Domain agents (hr_agent, tech_agent, finance_agent) are not meant to be
called directly by end users in this system; this orchestrator is the
front door.

`handle()` is also the tracing boundary (see ADR-011): it's wrapped with
Langfuse's `@observe`, so one call = one trace. A single CallbackHandler is
built per call and passed as `callbacks` into both the classification chain
and the routed agent's generation chain, so both nest as child spans of
that same trace instead of showing up as two unrelated traces.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langfuse import get_client, observe
from pydantic import BaseModel, Field

from adapters.openai_llm import OpenAILLMClient
from adapters.tracing import build_langchain_handler
from agents import finance_agent, hr_agent, tech_agent
from agents.base import DomainAgent
from domain.exceptions import ContentBlockedError
from domain.models import RAGResponse
from domain.moderation import ModerationAction
from factory import build_moderation_service
from services.moderation_service import ModerationService

Intent = Literal["hr", "tech", "finance", "unknown"]

_CLASSIFICATION_SYSTEM_PROMPT = (
    "Sos el orquestador de un sistema de soporte interno de una empresa "
    "SaaS. Tu única tarea es clasificar a qué departamento corresponde la "
    "consulta de un empleado. No respondas la consulta, solo clasificala."
)

_CLASSIFICATION_USER_TEMPLATE = (
    "Clasificá la siguiente consulta en uno de estos 4 valores:\n"
    "- 'hr': Recursos Humanos (sueldos, vacaciones, licencias, beneficios, "
    "modalidad de trabajo/trabajo remoto o híbrido, conducta, onboarding, "
    "desvinculación)\n"
    "- 'tech': IT Support / Tecnología (hardware, accesos, contraseñas, VPN, "
    "seguridad informática, entornos de desarrollo, y licencias/uso de "
    "herramientas de software en general -- mensajería, gestión de "
    "proyectos, diseño, IDEs, etc. -- sin importar el área que las use)\n"
    "- 'finance': Finanzas (gastos, reembolsos, tarjeta corporativa, "
    "facturación de proveedores, presupuesto, impuestos)\n"
    "- 'unknown': la consulta no corresponde a ninguno de los 3 dominios "
    "anteriores (por ejemplo Legal, Ventas, o algo no relacionado con la "
    "empresa)\n\n"
    "Consulta: {question}"
)

_UNKNOWN_MESSAGE = (
    "Esta consulta no corresponde a Recursos Humanos, IT/Tecnología ni "
    "Finanzas, que son los departamentos que puedo resolver. Por favor "
    "contactá al área correspondiente o reformulá tu pregunta si creés que "
    "sí aplica a uno de estos dominios."
)


class IntentClassification(BaseModel):
    intent: Intent = Field(description="Departamento correspondiente a la consulta.")
    reasoning: str = Field(
        description="Justificación breve (una oración) de la clasificación, para debugging de misclassifications."
    )


@dataclass(frozen=True)
class OrchestratorResponse:
    question: str
    intent: Intent
    reasoning: str
    rag_response: RAGResponse
    # Langfuse trace id for this call (None if tracing isn't configured) --
    # lets callers attach an LLM-as-judge score to this exact trace via the
    # Score API instead of just returning it in an HTTP response (ADR-011).
    trace_id: str | None = None


class Orchestrator:
    def __init__(
        self,
        classifier_llm: OpenAILLMClient,
        moderation: ModerationService,
        agents: dict[str, DomainAgent] | None = None,
    ) -> None:
        self._moderation = moderation
        self._agents = agents or {
            "hr": hr_agent.agent,
            "tech": tech_agent.agent,
            "finance": finance_agent.agent,
        }
        structured_llm = classifier_llm.model.with_structured_output(IntentClassification)
        prompt = ChatPromptTemplate.from_messages(
            [("system", _CLASSIFICATION_SYSTEM_PROMPT), ("user", _CLASSIFICATION_USER_TEMPLATE)]
        )
        self._classifier = prompt | structured_llm

    def classify(self, question: str, callbacks: list | None = None) -> IntentClassification:
        config = {"callbacks": callbacks} if callbacks else None
        return self._classifier.invoke({"question": question}, config=config)

    @observe(name="orchestrator.handle")
    def handle(self, question: str) -> OrchestratorResponse:
        _risks, action, reason = self._moderation.check(question)
        if action == ModerationAction.BLOCK:
            raise ContentBlockedError(reason)

        handler = build_langchain_handler()
        classification = self.classify(question, callbacks=[handler])
        agent = self._agents.get(classification.intent)

        if agent is None:
            rag_response = RAGResponse(
                user_question=question,
                system_answer=_UNKNOWN_MESSAGE,
                chunks_related=[],
            )
        else:
            rag_response = agent.ask(question, callbacks=[handler])

        return OrchestratorResponse(
            question=question,
            intent=classification.intent,
            reasoning=classification.reasoning,
            rag_response=rag_response,
            trace_id=get_client().get_current_trace_id(),
        )


def build_orchestrator(chat_model: str = "gpt-4o-mini") -> Orchestrator:
    api_key = os.getenv("OPENAI_API_KEY")
    # temperature=0: la clasificación es una tarea determinística (un label de
    # un enum cerrado), no generación de texto -- no queremos variabilidad
    # entre corridas para la misma pregunta.
    classifier_llm = OpenAILLMClient(model=chat_model, api_key=api_key, temperature=0)
    moderation = build_moderation_service()
    return Orchestrator(classifier_llm=classifier_llm, moderation=moderation)
