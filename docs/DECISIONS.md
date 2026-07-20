# Decisiones técnicas (ADR) — M2 → M3

- **ADR-001 — Código en `.py` + notebook delgado**: lógica real en `src/`; el notebook solo importa y muestra el flujo por secciones.
- **ADR-002 — Hexagonal envolviendo LangChain**: LangChain vive dentro de los `adapters/`; `ports/` define el contrato, no se disuelve la arquitectura de M2.
- **ADR-003 — Moderación + API migradas en paralelo**: no se dejaron como opcional ni se descartaron al pasar a multi-agente.
- **ADR-004 — LCEL puro, no `create_agent`/`langchain-classic`**: LangChain resolvió en 1.x (no 0.3.x); la consigna pide clasificación explícita + branching determinístico, no un agente autónomo con tool-calling.
- **ADR-005 — ChromaDB primario, FAISS sin migrar**: Chroma soporta multi-colección nativo (1 por dominio); FAISS queda como adapter alternativo del mismo port, no usado en el flujo actual.
- **ADR-006 — Clasificación con structured output**: `Literal["hr","tech","finance","unknown"]` + `reasoning` trazable — no texto libre, embeddings ni keywords.
- **ADR-007 — Moderación como gate único**: se sacó de `RAGPipeline` y vive solo en `Orchestrator.handle()`, para no auditar la misma pregunta dos veces.
- **ADR-008 — Fix real de misclassification (94%→100%)**: el bucket `tech` no cubría "herramientas de diseño"; se corrigió el prompt de clasificación, no el test.
- **ADR-009 — `temperature=0` en el clasificador**: sin esto la misma pregunta clasificaba distinto entre corridas (structured output no garantiza reproducibilidad por sí solo).
- **ADR-010 — Langfuse v4 (OTel-based), no v2**: el SDK instalado rehizo la API completa; `requirements.txt` estaba mal pineado a v2.
- **ADR-011 — Un trace de Langfuse por pregunta**: `@observe` en `Orchestrator.handle()` + un `CallbackHandler` por request, anidado vía contexto OTel (no hace falta pasar `trace_id` a mano). El evaluador asocia su score al mismo `trace_id` vía Score API.
- **ADR-012 — `test_queries.json` a 21 casos**: cobertura explícita de los 3 tipos de `BLOCK` + el caso `FLAG` (antes sin probar), más una regresión ambigua contra ADR-008.
