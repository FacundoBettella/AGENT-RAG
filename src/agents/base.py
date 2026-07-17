"""Shared factory for specialized RAG agents.

Each domain agent (hr_agent.py, tech_agent.py, finance_agent.py) is the
same underlying RAGPipeline (see services/pipeline.py) wired to a
different Chroma collection, knowledge base directory and system prompt.
This module holds the one place that wiring happens, so the 3 domain
modules only need to declare *what* makes them different, not *how* a
RAG agent is built.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.models import RAGResponse
from factory import FAQBundle, build_faq_bundle


@dataclass(frozen=True)
class DomainAgentConfig:
    name: str
    collection_name: str
    data_dir: str
    system_prompt: str


class DomainAgent:
    """Lazily builds its FAQBundle (indexer + pipeline) on first use, then
    reuses it — avoids re-embedding the knowledge base on every question.
    """

    def __init__(self, config: DomainAgentConfig) -> None:
        self.config = config
        self._bundle: FAQBundle | None = None

    def _get_bundle(self) -> FAQBundle:
        if self._bundle is None:
            self._bundle = build_faq_bundle(
                collection_name=self.config.collection_name,
                data_dir=self.config.data_dir,
                system_prompt=self.config.system_prompt,
            )
        return self._bundle

    def ask(self, question: str) -> RAGResponse:
        return self._get_bundle().pipeline.ask(question)
