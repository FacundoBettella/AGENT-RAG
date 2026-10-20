# Testing — fix-type-errors

**Modo:** test-after

Feature `sdd: false` (camino rápido): no hay escenarios `@s`. Contrato = "Cambio pedido": dejar `mypy` limpio sin cambiar el JSON observable de la API, y cubrir con tests reales las rutas y handlers tocados. Sin llamadas a OpenAI ni Langfuse (orquestador/agentes falsos inyectados en `app.state`, sin correr el lifespan; judge y push de score parcheados).

| Test | Qué verifica |
|---|---|
| `tests/test_routes.py::test_health_reports_chunks_per_agent` | `/api/health`: forma `{status, chunks_indexed}` |
| `tests/test_routes.py::test_query_returns_query_result_shape` | `/api/query`: JSON exacto `query_result` (chunks, similarity redondeada a 4, intent, reasoning) |
| `tests/test_routes.py::test_ingest_returns_ingest_result_shape` | `/api/ingest`: JSON exacto `ingest_result`; el agente recibe los documentos |
| `tests/test_routes.py::test_ingest_domain_without_registered_agent_is_400` | `/api/ingest` sin agente registrado: 400 + `{"error": "Dominio desconocido: ..."}` |
| `tests/test_routes.py::test_evaluate_returns_evaluate_result_with_score` | `/api/evaluate`: JSON exacto `evaluate_result` con `evaluation` como score; se empuja el score al `trace_id` |
| `tests/test_routes.py::test_evaluate_keeps_unparseable_evaluation_dict` | `/api/evaluate`: la evaluación no parseable (`{error, raw}`) se devuelve intacta |
| `tests/test_exception_handlers.py::test_content_blocked_error_maps_to_400_with_reason` | `ContentBlockedError` -> 400 `{"error": reason}` |
| `tests/test_exception_handlers.py::test_http_exception_maps_to_status_and_detail` | `HTTPException` -> status propio + `{"error": detail}` |
| `tests/test_exception_handlers.py::test_request_validation_error_maps_to_422` | body inválido -> 422 `{"error": ...}` mencionando el campo |
| `tests/test_exception_handlers.py::test_unexpected_exception_maps_to_500_with_message` | excepción genérica -> 500 `{"error": mensaje}` |
| `tests/test_faiss_store.py` (4 tests) | `FAISSStore` (tocado por el fix de tipos): store vacío, add+query, persistencia y recarga con `efSearch`, `add([])` sin persistir |

## Verificación de que los tests muerden

Mutaciones manuales (cada una rompió al menos un test; luego se restauró): status 400 -> 418 y 500 -> 501 en handlers, `documents_received=0` en ingest, `reasoning` vacío en query, `intent` fijo en evaluate, `write_index` eliminado y guard de `_save` neutralizado en `FAISSStore`.

Soporte: `pytest.ini` (`pythonpath = src tests`, `testpaths = tests`) y `tests/conftest.py` (fakes + fixture `client`).
