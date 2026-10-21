# Review — feature #1 answer-feedback

**Veredicto:** APPROVED

`./init.sh` verde (ruff, mypy 54 archivos, 29 tests pasan).

## Cobertura de escenarios (@s <-> test)
- @s1: [x] `test_query_returns_trace_id_when_tracing_is_enabled`, `test_query_returns_query_result_shape`
- @s2: [x] `test_query_returns_null_trace_id_when_tracing_is_disabled`
- @s3: [x] `test_helpful_vote_is_echoed_and_pushed_to_langfuse`, `test_helpful_feedback_creates_boolean_score_with_value_1`
- @s4: [x] `test_revote_not_helpful_is_pushed_again_for_the_same_trace`, `test_revote_reuses_the_score_id_...`, `test_different_traces_get_different_score_ids`
- @s5: [x] un test por caso, ambos verifican forma `{"error": str}` y `pushed == []`: `test_trace_id_with_invalid_format_is_422_and_pushes_nothing`, `test_body_without_boolean_helpful_is_422_and_pushes_nothing`
- @s6: [x] `test_feedback_with_tracing_disabled_is_503_and_pushes_nothing` + 3 tests de `is_tracing_enabled`

## Disciplina de testing (TDD estricto)
- Produccion sin test que la pida: NO. Todo el codigo nuevo (schemas, ruta, adapter, trace_id en query) tiene test que lo exige.
- Evidencia Rojo->Verde->Refactor: SI (testing.md, con mutaciones manuales documentadas para los tests verdes a la primera).

## Puntos marcados por el developer
- `is_tracing_enabled()` (src/adapters/tracing.py:41-48): aceptable. El null de trace_id en @s2 viene de `get_client().get_current_trace_id()` (src/agents/orchestrator.py:145), es decir del SDK, y la ruta solo lo propaga; ambos criterios coinciden en el caso normal (keys ausentes / flag en false). Riesgo menor: si el SDK deshabilitara por otra causa, feedback daria 200 sin registrar. No bloqueante.
- Regex `^[0-9a-f]{32}$` (src/api/schemas.py:79): aceptable. Los trace ids de Langfuse/OTel son hex en minuscula; el spec dice "32 hex" y el .feature usa minuscula. Mayusculas dan 422, coherente con el id real. No bloqueante.
- `helpful: bool` laxo: aceptable. Spec (linea 11) y @s5 piden "bool"; el caso cubierto es campo ausente. Opcional endurecer con `StrictBool` en un cambio futuro; no esta en el contrato.
- Tests verdes a la primera: muerden. @s2 asserta `is None` (un `or "x"` en la ruta lo rompe), re-voto asserta la secuencia completa de pushes y score_id igual/distinto, 422 por helpful faltante asserta 422 + `pushed == []` (un default lo rompe).

## Calidad
- Funciones cortas, capas respetadas (ruta -> adapter), tipado completo, sin prints. Sin hallazgos.
- Nota menor: `from conftest import FakeOrchestrator` en tests/test_routes.py:8 depende del rootdir/pythonpath de pytest; funciona hoy.

## Checkpoints
- C1..C5: [x]
- C6: [x]

## Cambios requeridos
Ninguno.
