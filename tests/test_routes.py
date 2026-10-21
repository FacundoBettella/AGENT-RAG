from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import evaluate
from conftest import FakeOrchestrator

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"

CHUNK_JSON = {
    "content": "Las vacaciones se solicitan en el portal.",
    "source": "hr_docs/vacaciones.md",
    "similarity": 0.9123,
}


def test_health_reports_chunks_per_agent(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "chunks_indexed": {"hr": 10, "tech": 5}}


def test_query_returns_query_result_shape(client: TestClient) -> None:
    response = client.post("/api/query", json={"question": "¿Cómo pido vacaciones?"})

    assert response.status_code == 200
    assert response.json() == {
        "query_result": {
            "user_question": "¿Cómo pido vacaciones?",
            "system_answer": "Desde el portal de RRHH.",
            "chunks_related": [CHUNK_JSON],
            "intent": "hr",
            "reasoning": "habla de vacaciones",
            "trace_id": "trace-1",
        }
    }


def test_query_returns_trace_id_when_tracing_is_enabled(client: TestClient) -> None:
    app.state.orchestrator = FakeOrchestrator(trace_id=TRACE_ID)

    response = client.post("/api/query", json={"question": "¿Cómo pido vacaciones?"})

    assert response.status_code == 200
    assert response.json()["query_result"]["trace_id"] == TRACE_ID


def test_query_returns_null_trace_id_when_tracing_is_disabled(client: TestClient) -> None:
    app.state.orchestrator = FakeOrchestrator(trace_id=None)

    response = client.post("/api/query", json={"question": "¿Cómo pido vacaciones?"})

    assert response.status_code == 200
    assert response.json()["query_result"]["trace_id"] is None


def test_ingest_returns_ingest_result_shape(client: TestClient, agents: dict[str, Any]) -> None:
    response = client.post("/api/ingest", json={"domain": "hr", "documents": ["a", "b"]})

    assert response.status_code == 200
    assert response.json() == {
        "ingest_result": {
            "domain": "hr",
            "documents_received": 2,
            "chunks_indexed": 3,
            "total_in_store": 10,
        }
    }
    assert agents["hr"].ingested == [["a", "b"]]


def test_ingest_domain_without_registered_agent_is_400(client: TestClient) -> None:
    # "finance" is a valid Domain but this app has no agent registered for it.
    response = client.post("/api/ingest", json={"domain": "finance", "documents": ["a"]})

    assert response.status_code == 400
    assert response.json() == {"error": "Dominio desconocido: finance"}


@pytest.fixture
def stub_evaluation(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replaces the LLM judge and the Langfuse score push; exposes what happened."""
    state: dict[str, Any] = {"result": {}, "pushed": []}
    monkeypatch.setattr(evaluate, "_get_evaluator_llm", lambda: object())
    monkeypatch.setattr(evaluate, "evaluate_response", lambda _llm, _resp: state["result"])
    monkeypatch.setattr(
        evaluate,
        "push_evaluation_score",
        lambda trace_id, ev: state["pushed"].append((trace_id, ev)),
    )
    return state


def test_evaluate_returns_evaluate_result_with_score(
    client: TestClient, stub_evaluation: dict[str, Any]
) -> None:
    score = {
        "score": 8,
        "relevancia": 3,
        "precision": 3,
        "completitud": 2,
        "justificacion": "Responde bien.",
    }
    stub_evaluation["result"] = score

    response = client.post("/api/evaluate", json={"question": "¿Cómo pido vacaciones?"})

    assert response.status_code == 200
    assert response.json() == {
        "evaluate_result": {
            "user_question": "¿Cómo pido vacaciones?",
            "system_answer": "Desde el portal de RRHH.",
            "chunks_related": [CHUNK_JSON],
            "intent": "hr",
            "evaluation": score,
        }
    }
    assert stub_evaluation["pushed"] == [("trace-1", score)]


def test_evaluate_keeps_unparseable_evaluation_dict(
    client: TestClient, stub_evaluation: dict[str, Any]
) -> None:
    error = {"error": "No se pudo parsear la evaluación", "raw": "basura"}
    stub_evaluation["result"] = error

    response = client.post("/api/evaluate", json={"question": "hola"})

    assert response.status_code == 200
    assert response.json()["evaluate_result"]["evaluation"] == error
