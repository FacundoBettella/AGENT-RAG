from fastapi.testclient import TestClient

from api.main import app
from conftest import FakeOrchestrator
from domain.exceptions import ContentBlockedError


def test_content_blocked_error_maps_to_400_with_reason(client: TestClient) -> None:
    app.state.orchestrator = FakeOrchestrator(error=ContentBlockedError("contenido bloqueado"))

    response = client.post("/api/query", json={"question": "algo prohibido"})

    assert response.status_code == 400
    assert response.json() == {"error": "contenido bloqueado"}


def test_http_exception_maps_to_status_and_detail(client: TestClient) -> None:
    response = client.post("/api/ingest", json={"domain": "finance", "documents": []})

    assert response.status_code == 400
    assert response.json() == {"error": "Dominio desconocido: finance"}


def test_request_validation_error_maps_to_422(client: TestClient) -> None:
    response = client.post("/api/query", json={})

    assert response.status_code == 422
    body = response.json()
    assert list(body) == ["error"]
    assert "question" in body["error"]


def test_unexpected_exception_maps_to_500_with_message(client: TestClient) -> None:
    app.state.orchestrator = FakeOrchestrator(error=RuntimeError("boom"))

    response = client.post("/api/query", json={"question": "hola"})

    assert response.status_code == 500
    assert response.json() == {"error": "boom"}
