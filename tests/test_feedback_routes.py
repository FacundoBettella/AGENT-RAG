from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.routes import feedback

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


@pytest.fixture
def stub_feedback(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replaces the Langfuse tracing check and score push; exposes what happened."""
    state: dict[str, Any] = {"pushed": []}
    monkeypatch.setattr(feedback, "is_tracing_enabled", lambda: True)
    monkeypatch.setattr(
        feedback,
        "push_user_feedback",
        lambda trace_id, helpful: state["pushed"].append((trace_id, helpful)),
    )
    return state


def test_helpful_vote_is_echoed_and_pushed_to_langfuse(
    client: TestClient, stub_feedback: dict[str, Any]
) -> None:
    response = client.post("/api/feedback", json={"trace_id": TRACE_ID, "helpful": True})

    assert response.status_code == 200
    assert response.json() == {"feedback_result": {"trace_id": TRACE_ID, "helpful": True}}
    assert stub_feedback["pushed"] == [(TRACE_ID, True)]


def test_revote_not_helpful_is_pushed_again_for_the_same_trace(
    client: TestClient, stub_feedback: dict[str, Any]
) -> None:
    client.post("/api/feedback", json={"trace_id": TRACE_ID, "helpful": True})

    response = client.post("/api/feedback", json={"trace_id": TRACE_ID, "helpful": False})

    assert response.status_code == 200
    assert response.json() == {"feedback_result": {"trace_id": TRACE_ID, "helpful": False}}
    assert stub_feedback["pushed"] == [(TRACE_ID, True), (TRACE_ID, False)]


def test_trace_id_with_invalid_format_is_422_and_pushes_nothing(
    client: TestClient, stub_feedback: dict[str, Any]
) -> None:
    response = client.post("/api/feedback", json={"trace_id": "not-a-32-char-hex", "helpful": True})

    assert response.status_code == 422
    assert isinstance(response.json()["error"], str)
    assert list(response.json()) == ["error"]
    assert stub_feedback["pushed"] == []


def test_body_without_boolean_helpful_is_422_and_pushes_nothing(
    client: TestClient, stub_feedback: dict[str, Any]
) -> None:
    response = client.post("/api/feedback", json={"trace_id": TRACE_ID})

    assert response.status_code == 422
    assert isinstance(response.json()["error"], str)
    assert list(response.json()) == ["error"]
    assert stub_feedback["pushed"] == []


def test_feedback_with_tracing_disabled_is_503_and_pushes_nothing(
    client: TestClient, stub_feedback: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(feedback, "is_tracing_enabled", lambda: False)

    response = client.post("/api/feedback", json={"trace_id": TRACE_ID, "helpful": True})

    assert response.status_code == 503
    assert response.json() == {"error": "Tracing deshabilitado: el feedback no se registró"}
    assert stub_feedback["pushed"] == []
