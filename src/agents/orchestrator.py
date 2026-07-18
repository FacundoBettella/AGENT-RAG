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
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from adapters.openai_llm import OpenAILLMClient
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
    "conducta, onboarding, desvinculación)\n"
    "- 'tech': IT Support / Tecnología (hardware, accesos, contraseñas, VPN, "
    "seguridad informática, software, entornos de desarrollo)\n"
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

    def classify(self, question: str) -> IntentClassification:
        return self._classifier.invoke({"question": question})

    def handle(self, question: str) -> OrchestratorResponse:
        risks, action, reason = self._moderation.check(question)
        if action == ModerationAction.BLOCK:
            raise ContentBlockedError(reason)

        classification = self.classify(question)
        agent = self._agents.get(classification.intent)

        if agent is None:
            rag_response = RAGResponse(
                user_question=question,
                system_answer=_UNKNOWN_MESSAGE,
                chunks_related=[],
            )
        else:
            rag_response = agent.ask(question)

        return OrchestratorResponse(
            question=question,
            intent=classification.intent,
            reasoning=classification.reasoning,
            rag_response=rag_response,
        )


def build_orchestrator(chat_model: str = "gpt-4o-mini") -> Orchestrator:
    api_key = os.getenv("OPENAI_API_KEY")
    classifier_llm = OpenAILLMClient(model=chat_model, api_key=api_key)
    moderation = build_moderation_service()
    return Orchestrator(classifier_llm=classifier_llm, moderation=moderation)
