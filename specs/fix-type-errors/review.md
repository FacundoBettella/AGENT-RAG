# Review — feature 2 fix-type-errors

**Veredicto:** APPROVED

## Cobertura (comportamiento <-> test)
- JSON de /query, /ingest, /evaluate (con score y con evaluacion no parseable), /health: [x] `tests/test_routes.py` (asserts de JSON exacto).
- Exception handlers (400/HTTPException/422/500): [x] `tests/test_exception_handlers.py`.
- FAISSStore (guard de `_save`, downcast/efSearch en recarga): [x] `tests/test_faiss_store.py`.

## Disciplina de testing (test-after)
- Tests triviales: NO. Asserts de JSON exacto; el developer registro mutaciones que rompen tests.
- Sin red: fakes inyectados en `app.state` sin correr el lifespan; judge y push de Langfuse parcheados.

## Calidad
- Rutas: el dict pasa por el mismo response model que antes aplicaba FastAPI, asi que el JSON no cambia. Los tests lo fijan.
- `cast` en exception_handlers: aceptable. Starlette tipa los handlers como `(Request, Exception)` y solo despacha la clase registrada. Comentado.
- `cast` + `faiss.downcast_index` en faiss_store: correcto. Se persiste y guarda `index` y se configura `efSearch` sobre el downcast.
- Early-return en `_save` con `_index is None`: solo cambia el caso que antes habria fallado. Cubierto por el test `add([])`.
- Scripts: guard `isinstance(sys.stdout, io.TextIOWrapper)`, sin `type: ignore`.
- Sin `# type: ignore` generalizados. `mypy.ini` y `ruff.toml` los agrego el tech-lead y quedan fuera del review.

## Verificacion
- `./init.sh`: verde (ruff OK, mypy "no issues found in 51 source files", 14 tests passed).

## Checkpoints
- C1..C5: [x]. C6: N/A (sdd: false).
