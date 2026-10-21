# answer-feedback (#1)

## Propósito

Registrar en Langfuse, asociado a la traza de esa consulta, si una respuesta de `/api/query` le fue útil al usuario.

## Contrato

- **Cambio en `POST /api/query`**: `query_result` suma `trace_id: str | null` (null si tracing está deshabilitado).
- **Nuevo `POST /api/feedback`**
  - Request: `{"trace_id": str, "helpful": bool}`.
  - 200: `{"feedback_result": {"trace_id": str, "helpful": bool}}`.
  - 422: body inválido o `trace_id` con formato inválido (no 32 hex) → `{"error": str}` (handler existente).
  - 503: tracing deshabilitado → `{"error": "Tracing deshabilitado: el feedback no se registró"}`.
- **Efecto en Langfuse**: score `name="user_feedback"`, `data_type="BOOLEAN"`, `value` 1 (útil) / 0 (no útil), sobre `trace_id`, con `score_id` determinístico derivado del `trace_id`.

## Decisiones

1. **Ruta `POST /api/feedback`** en `routes/feedback.py`, bajo el prefijo `/api` como las demás.
2. **Sin comentario libre**: solo `helpful`. La descripción pide útil/no útil; sumar `comment` después es aditivo y evita pasar texto libre por moderación.
3. **Score BOOLEAN `user_feedback`**: tipo nativo de Langfuse para binarios; descartado NUMERIC ±1 porque no aporta y complica dashboards.
4. **Push en `adapters/tracing.py`** (`push_user_feedback`), hermano de `push_evaluation_score`: Langfuse solo vive en adapters (ADR-002).
5. **Sin auth**: ningún endpoint de la API la tiene hoy; fuera de alcance.
6. **Cualquier respuesta es votable** (hr/tech/finance/unknown): el endpoint no conoce el intent; la traza ya lo tiene.
7. **`trace_id` como campo de `query_result`**, null sin tracing. Descartado header `X-Trace-Id`: el frontend ya parsea el body, y un header exige exponerlo en CORS.
8. **Tracing deshabilitado → 503** con error explícito. Descartado 200 no-op: le haría creer al cliente que el voto quedó registrado cuando se perdió.
9. **Solo se valida formato del `trace_id`** (32 hex) → 422. Descartado consultar existencia en Langfuse (404): suma una llamada extra por voto y da falsos 404 por la ingesta asíncrona.
10. **Re-voto pisa**: `score_id` determinístico derivado del `trace_id`, un único voto por respuesta. Descartado acumular votos: ensucia las métricas con duplicados y el último voto refleja la opinión final.
