from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from domain.models import Chunk, RAGResponse, RetrievedChunk


def make_rag_response() -> RAGResponse:
    chunk = Chunk(
        content="Las vacaciones se solicitan en el portal.",
        document_id="doc-1",
        chunk_index=0,
        metadata={"source": "hr_docs/vacaciones.md"},
    )
    return RAGResponse(
        user_question="¿Cómo pido vacaciones?",
        system_answer="Desde el portal de RRHH.",
        chunks_related=[RetrievedChunk(chunk=chunk, similarity=0.912345)],
    )


@dataclass
class FakeOrchestratorResult:
    rag_response: RAGResponse
    intent: str = "hr"
    reasoning: str = "habla de vacaciones"
    trace_id: str | None = "trace-1"


class FakeOrchestrator:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def handle(self, question: str) -> FakeOrchestratorResult:
        if self._error is not None:
            raise self._error
        return FakeOrchestratorResult(rag_response=make_rag_response())


@dataclass
class FakeAgent:
    chunks_per_ingest: int = 3
    total: int = 10
    ingested: list[list[str]] = field(default_factory=list)

    def count(self) -> int:
        return self.total

    def ingest_texts(self, texts: list[str]) -> int:
        self.ingested.append(texts)
        return self.chunks_per_ingest


@pytest.fixture
def agents() -> dict[str, Any]:
    return {"hr": FakeAgent(), "tech": FakeAgent(total=5)}


@pytest.fixture
def client(agents: dict[str, Any]) -> Iterator[TestClient]:
    # No `with TestClient(...)`: the lifespan (which builds the real
    # orchestrator / OpenAI clients) never runs; state is injected here.
    app.state.orchestrator = FakeOrchestrator()
    app.state.agents = agents
    yield TestClient(app, raise_server_exceptions=False)
