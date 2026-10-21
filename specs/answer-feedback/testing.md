# Testing — answer-feedback (#1)

**Modo:** TDD estricto

Tests en `tests/` (pytest, `TestClient` + monkeypatch del módulo de la ruta, mismo patrón que `/api/evaluate`; el SDK de Langfuse se reemplaza por un fake en los tests del adapter, nunca hay red).

## Trazabilidad

- @s1 (query devuelve trace_id con tracing habilitado)
  → `tests/test_routes.py::test_query_returns_trace_id_when_tracing_is_enabled`
  → `tests/test_routes.py::test_query_returns_query_result_shape` (ajustado: el shape ahora incluye `trace_id`)
- @s2 (query devuelve trace_id null con tracing deshabilitado)
  → `tests/test_routes.py::test_query_returns_null_trace_id_when_tracing_is_disabled`
- @s3 (voto útil -> score BOOLEAN user_feedback, value 1, score_id determinístico)
  → `tests/test_feedback_routes.py::test_helpful_vote_is_echoed_and_pushed_to_langfuse` (200, body, push al adapter)
  → `tests/test_tracing.py::test_helpful_feedback_creates_boolean_score_with_value_1` (name, data_type, value, trace_id, score_id)
- @s4 (re-voto pisa el anterior: value 0 y mismo score_id)
  → `tests/test_feedback_routes.py::test_revote_not_helpful_is_pushed_again_for_the_same_trace`
  → `tests/test_tracing.py::test_not_helpful_feedback_creates_boolean_score_with_value_0`
  → `tests/test_tracing.py::test_revote_reuses_the_score_id_so_langfuse_overwrites_the_previous_vote`
  → `tests/test_tracing.py::test_different_traces_get_different_score_ids` (el id deriva del trace_id, no es constante)
- @s5 (422 con forma `{"error": ...}` y sin score a Langfuse; un test por caso)
  → `tests/test_feedback_routes.py::test_trace_id_with_invalid_format_is_422_and_pushes_nothing`
  → `tests/test_feedback_routes.py::test_body_without_boolean_helpful_is_422_and_pushes_nothing`
- @s6 (tracing deshabilitado -> 503 con mensaje explícito, sin push)
  → `tests/test_feedback_routes.py::test_feedback_with_tracing_disabled_is_503_and_pushes_nothing`
  → `tests/test_tracing.py::test_tracing_is_enabled_when_both_keys_are_configured`,
    `test_tracing_is_disabled_when_a_key_is_missing[PUBLIC|SECRET]`,
    `test_tracing_is_disabled_when_explicitly_turned_off` (cómo se decide "tracing deshabilitado")

## Notas del ciclo

- @s2, el re-voto con mismo score_id y el caso 422 por `helpful` faltante pasaron a la primera (la generalización ya venía de ciclos previos). Se verificó a mano que muerden: `trace_id or "x"` en la ruta rompe @s2; `score_id` aleatorio o constante rompe los tests de score_id; `helpful: bool = True` rompe el 422 por `helpful` faltante.
- `is_tracing_enabled()` replica las condiciones del SDK (ambas keys presentes y `LANGFUSE_TRACING_ENABLED != false`) porque el SDK no expone un flag público.
- `trace_id` se valida como 32 hex en minúscula (`^[0-9a-f]{32}$`), formato de los ids de Langfuse.
- `score_id` = `user_feedback-<trace_id>`.
