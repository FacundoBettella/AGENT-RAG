# Arquitectura

> El "por qué" de cada decisión técnica (LangChain vs. código custom, LCEL vs.
> `create_agent`, Chroma vs. FAISS, Langfuse v4 vs. v2, etc.) está documentado como ADRs en
> [`docs/DECISIONS.md`](DECISIONS.md). Este archivo documenta el "cómo".

Arquitectura hexagonal: la lógica de negocio no conoce a LangChain directamente, lo usa
*a través* de los adapters.

```text
domain/     → DTOs inmutables (Chunk, RAGResponse) + ModerationAction + excepciones
ports/      → Protocols (Embedder, VectorStore, LLMClient, LogRepository)
adapters/   → implementaciones concretas -- LangChain vive ACÁ adentro
              (chroma_store.py usa langchain_chroma, openai_llm.py usa langchain_openai,
              tracing.py usa el CallbackHandler de Langfuse)
services/   → Chunker, Indexer, Retriever, RAGPipeline (chain LCEL), ModerationService, evaluator
agents/     → DomainAgent (HR/Tech/Finance) + Orchestrator (clasificación + ruteo)
api/        → FastAPI: expone el orquestador por HTTP
factory.py  → único lugar que instancia adapters concretos
```

## ¿Qué es "hexagonal" y cómo funciona acá?

La idea (puertos y adaptadores): la lógica de negocio (`services/`, `agents/`) depende de
**interfaces** (`ports/`, `Protocol` de Python), nunca de una librería o proveedor concreto.
Cada implementación real (`adapters/`) cumple esa interfaz, y **un solo lugar** (`factory.py`)
decide cuál usar. Así se puede cambiar de proveedor sin tocar la lógica de negocio.

Ejemplo concreto de este repo: `ports/vector_store.py` define el contrato (`add`/`query`/
`count`). `ChromaStore` y `FAISSStore` lo implementan; `Retriever` y `RAGPipeline` solo
conocen el `Protocol`, nunca importan Chroma o FAISS directamente. `factory.py` es el único
que elige `ChromaStore` (ver ADR-005). Mismo patrón con `ports/llm.py` (`OpenAILLMClient` es
la única implementación hoy, pero nada impide agregar un adapter para otro proveedor).

Matiz importante: a diferencia del hexagonal "de libro", acá los `ports` sí exponen tipos de
LangChain (`BaseChatModel`) a propósito, para que el resto del código pueda componer chains
LCEL (`prompt | llm.model | parser`) sin reimplementar esa composición — LangChain vive
*dentro* de los adapters, pero su tipo de "modelo componible" se deja pasar por el port (ver
ADR-002).

## Flujos

### 1. Consulta end-to-end (`Orchestrator.handle()`)

Este es el flujo real por cada pregunta que entra al sistema, sea por API, script o notebook:

```text
pregunta
   │
   ▼
① Moderación (3 capas, ver abajo) ──► BLOCK ──► ContentBlockedError (corta acá, 0 tokens gastados)
   │ ALLOW / FLAG
   ▼
② Clasificación de intención (LLM, structured output, temperature=0)
   │   hr | tech | finance | unknown
   ▼
③ Enrutamiento condicional
   │
   ├── unknown ──► respuesta fija "fuera de alcance" (no llama a ningún agente)
   │
   └── hr/tech/finance ──► Agente de dominio elegido:
                              retrieve (top-k Chroma) → chain LCEL
                              (prompt | chat_model | parser) → respuesta
   ▼
OrchestratorResponse(question, intent, reasoning, rag_response, trace_id)
```

Los 3 agentes de dominio (`agents/hr_agent.py`, `tech_agent.py`, `finance_agent.py`) son la
misma clase `DomainAgent → RAGPipeline`, parametrizada con distinta colección de Chroma,
carpeta de `data/` y system prompt (`agents/base.py`). El orquestador es el **único** punto
de entrada — los agentes de dominio no se llaman directos en producción.

### 2. Ingesta (perezosa, por colección)

```text
primer .ask() a un dominio
   │
   ▼
¿su colección de Chroma está vacía? ──► no ──► usa lo que ya está indexado
   │ sí
   ▼
data/<dominio>_docs/*.txt → TextLoader → Chunker (RecursiveCharacterTextSplitter)
   → OpenAIEmbeddings → Chroma.add() (colección propia del dominio)
```

Las 3 colecciones (`hr_docs`, `tech_docs`, `finance_docs`) viven en un mismo
`persist_directory` (`.chroma/`) — ChromaDB soporta múltiples colecciones nombradas en un
solo cliente persistente (ver ADR-005).

### 3. Tracing (Langfuse)

```text
Orchestrator.handle()  ──@observe──►  abre 1 span raíz = 1 trace por pregunta
   │
   ├─ classify()  (callbacks=[handler]) ──► span "chain" + span "generation" (clasificador)
   │
   └─ agent.ask() (callbacks=[handler]) ──► span "chain" + span "generation" (respuesta)
```

Un `CallbackHandler` nuevo por request se pasa a ambas llamadas; como corren dentro del
span abierto por `@observe`, anidan automáticamente bajo el mismo trace (contexto de
OpenTelemetry). Si `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY` no están seteadas, el cliente se
autodeshabilita con un warning — el sistema responde igual, tracing es best-effort, no una
dependencia dura (ver ADR-010/011).

### 4. Evaluación (bonus — LLM-as-judge + Score API)

```text
OrchestratorResponse (ya con trace_id)
   │
   ▼
evaluate_response() ──► LLM juez puntúa 0-10 (relevancia / precisión / completitud)
   │
   ▼
push_evaluation_score(trace_id, evaluación) ──► Langfuse Score API
                                                 (el score queda asociado al trace de esa pregunta)
```

Conectado en `POST /api/evaluate` y en `scripts/03_evaluate.py`.

## Seguridad — capas de validación pre-LLM

3 capas corren **antes** de gastar cualquier token, dentro de `Orchestrator.handle()`:

| Capa | Qué detecta | Técnica | Acción |
|---|---|---|---|
| 1 — Datos sensibles | Tarjetas de crédito (Visa/MC/Amex), CUIT/CUIL, SSN | Regex | BLOCK |
| 2 — Lenguaje abusivo | Hate speech, violencia, autolesión, cyber abuse | Keywords | BLOCK |
| 3 — Prompt injection | Framing adversarial (`roleplay`, `ignore instructions`, etc.) + token sensible | Keywords combinados | BLOCK / FLAG |

Todo evento (`ALLOW`/`FLAG`/`BLOCK`) se audita en `logs/moderation_events.jsonl` (texto
original hasheado, nunca en claro; retención distinta según severidad). Si el resultado es
`BLOCK`, se lanza `ContentBlockedError` y la API responde `400` sin llegar a clasificar ni a
llamar a OpenAI. `FLAG` no bloquea: queda en el log de auditoría y la pregunta se responde
normal.

## Producción y notas operativas

- **Chroma** (`.chroma/`, en la raíz del proyecto) y **logs** (`logs/moderation_events.jsonl`)
  se resuelven siempre contra la raíz del repo (`factory.py::_resolve`), nunca contra el
  directorio desde donde arrancaste el proceso — así el mismo archivo se usa sin importar si
  lanzás el servidor desde la raíz o desde `src/`.
- **Para producción**: `.chroma/` es un directorio local en disco — no sirve tal cual para
  múltiples réplicas/contenedores sin un volumen compartido. A esa escala conviene un Chroma
  en modo cliente-servidor (o un vector store gestionado) en vez del `PersistentClient` local
  que usa `ChromaStore` hoy.
- **Logs de moderación**: hoy son un `.jsonl` en disco (ver capas de seguridad, arriba). En
  producción conviene mandarlos a un sistema centralizado (no un archivo local por instancia)
  para que la auditoría sobreviva a un restart/redeploy.
- **Langfuse**: ver flujo #3 más arriba — tracing es asíncrono (batch en background thread),
  no bloquea el request; si no hay credenciales, se desactiva solo.

## Estructura de directorios

```text
├── multi_agent_system.ipynb
├── test_queries.json          ← 21 casos (12 domain + 3 out_of_scope + 2 ambiguous + 4 moderation)
├── data/{hr,tech,finance}_docs/
├── logs/moderation_events.jsonl   (auto-generado)
├── docs/DECISIONS.md          ← ADRs (el "por qué" de cada decisión técnica)
├── src/
│   ├── domain/     modelos, ModerationAction, excepciones
│   ├── ports/      Protocols (Embedder, VectorStore, LLMClient, LogRepository)
│   ├── adapters/   OpenAI, Chroma, FAISS, TextLoader, JsonLog, tracing (Langfuse)
│   ├── services/   Chunker, Indexer, Retriever, RAGPipeline, ModerationService, evaluator
│   ├── agents/     hr_agent.py, tech_agent.py, finance_agent.py, orchestrator.py, base.py
│   ├── api/        FastAPI app + routes (query, evaluate, ingest, health)
│   └── factory.py
└── scripts/        01_ingest, 02_query, 03_evaluate, 04_serve, 05_test_routing
```

## Limitaciones conocidas

- **Ingesta no incremental**: si editás un `.txt` después del primer uso, no se re-embebe
  solo — hay que borrar `.chroma/` y volver a ingestar. Tampoco hay upsert idempotente
  (correr la ingesta dos veces duplica contenido).
- **FAISS no migrado a LangChain**: sigue siendo un adapter válido del mismo port, pero no
  se usa en el flujo multi-agente actual (ADR-005).
- **Sin memoria conversacional**: cada pregunta se procesa de forma independiente.
- **Routing single-hop**: el orquestador elige un único dominio por pregunta; una consulta
  genuinamente compuesta entre dos dominios no se divide ni se responde con múltiples
  agentes (ver casos `amb-01`/`amb-02` en `test_queries.json`).
