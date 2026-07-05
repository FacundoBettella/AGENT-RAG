# M2 Project — FAQ Chatbot con RAG

## Contexto y Objetivos

Eres un/a ingeniero/a de IA en una empresa de HR SaaS con mucha documentación. El
equipo de soporte al cliente recibe más de 200 preguntas repetitivas al día sobre políticas,
funcionalidades y procedimientos que ya están documentados en FAQs internas y guías. Tu
equipo necesita un Chatbot inteligente de soporte para FAQs que pueda responder al
instante recuperando información relevante de la documentación de la empresa, sin requerir
búsquedas manuales ni intervención de agentes.

## Objetivos

- Implementar un sistema de FAQs basado en RAG que procese un documento de texto
  plano, lo divida en chunks de forma inteligente (mínimo 20 chunks), genere embeddings y
  los almacene para una recuperación eficiente.
- Construir un pipeline de consulta que acepte preguntas de usuarios, realice búsqueda
  vectorial (ANN/HNSW), recupere los chunks relevantes y genere respuestas precisas con
  un LLM.
- El sistema debe devolver JSON estructurado con `user_question`, `system_answer` y
  `chunks_related` para asegurar transparencia y auditabilidad.
- **Opcional**: implementar un agente evaluador que puntúe la calidad de la respuesta (0–10)
  según la relevancia de los chunks, la precisión y la completitud.

## Arquitectura

```
domain/     → DTOs inmutables (FAQDocument, Chunk, RAGResponse) + excepciones
ports/      → Protocols/interfaces (Embedder, VectorStore, LLMClient, LogRepository)
adapters/   → implementaciones concretas (OpenAI, ChromaDB, TextLoader, JsonLog)
services/   → lógica de negocio (Chunker, Retriever, Pipeline, ModerationService)
factory.py  → único lugar que importa adapters concretos
```

## Vector Store — FAISS y tipos de índice

**FAISS** (Facebook AI Similarity Search) es la *librería* que implementa los algoritmos de búsqueda vectorial. No es un tipo de índice en sí mismo — es el motor que los contiene. ChromaDB usa HNSW internamente; FAISS te da acceso directo a cada tipo.

### Qué es cada tipo

| Tipo | Estrategia | Exactitud | Velocidad | Memoria |
|---|---|---|---|---|
| **Flat** | Compara contra todos los vectores (fuerza bruta) | 100% | Lenta a escala | Alta |
| **HNSW** | Grafo multicapa: capas altas saltan lejos, capas bajas refinan | ~95-99% | Muy rápida | Media-alta |
| **IVF** | Agrupa vectores en clusters; busca solo en los clusters cercanos | ~90-95% | Muy rápida a escala | Media |
| **PQ** | Comprime vectores para ahorrar RAM (como foto en baja resolución) | ~85-90% | Rápida | Muy baja |

### Comparativa visual

```
Exactitud   Flat  ████████████████████████  100%
            HNSW  ████████████████████      ~97%
            IVF   ████████████████          ~92%
            PQ    ████████████              ~87%

Velocidad   Flat  ████
            HNSW  ████████████████
            IVF   ████████████████████
            PQ    ████████████████████████

Memoria     Flat  ████████████████████████
            HNSW  ████████████████
            IVF   ████████████
            PQ    ████
```

### Elección para este proyecto: `IndexHNSWFlat`

Con ~20-50 chunks cualquier índice sería igual de rápido, pero se usa HNSW porque:

- Es el estándar en producción para RAG systems reales
- Ofrece el mejor balance exactitud/velocidad sin necesitar entrenamiento previo (como IVF)

### Dónde entra FAISS en la arquitectura

```
ports/vector_store.py     → Protocol (interfaz)
adapters/chroma_store.py  → implementación con ChromaDB  (usa HNSW internamente)
adapters/faiss_store.py   → implementación con FAISS     (IndexHNSWFlat explícito)
factory.py                → elige cuál usar
```

Son adapters intercambiables. El pipeline no sabe cuál está corriendo.

---

## Seguridad — Capas de validación pre-OpenAI

El sistema aplica 3 capas de validación **antes** de enviar cualquier request a OpenAI. Si una pregunta es bloqueada, se devuelve un JSON de error y **no se consumen tokens**.

| Capa | Qué detecta | Técnica | Acción |
|---|---|---|---|
| 1 — Datos sensibles | Tarjetas de crédito (Visa/MC/Amex), CUIT/CUIL, SSN | Regex | BLOCK |
| 2 — Lenguaje abusivo | Hate speech, violencia, autolesión, cyber abuse | Keywords | BLOCK |
| 3 — Prompt injection | Framing adversarial (`roleplay`, `ignore instructions`, etc.) + tokens sensibles | Keywords combinados | BLOCK / FLAG |

Todos los eventos de moderación se registran en `logs/moderation_events.jsonl` (campos hasheados para GDPR).

**Flujo por pregunta:**

```
pregunta → [Capa 1] → [Capa 2] → [Capa 3] → embeddings (OpenAI) → LLM (OpenAI)
```

Si la pregunta es bloqueada en cualquier capa, el pipeline se detiene y devuelve:

```json
{"error": "contenido_bloqueado", "detalle": "<motivo>"}
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Completar OPENAI_API_KEY y LOG_HASH_SALT en .env
```

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `OPENAI_API_KEY` | API key de OpenAI | — |
| `LOG_HASH_SALT` | Salt para hashear inputs en los logs (GDPR) | `m2-default-salt-change-me` |
| `LOGS_DIR` | Carpeta para logs de moderación | `logs` |

## Uso

```bash
# 1. Ingestar el documento de FAQs
python scripts/01_ingest.py

# 2. Verificar embeddings generados
python scripts/02_embed.py

# 3. Consultar el sistema
python scripts/03_query.py

# 4. Evaluar calidad (opcional)
python scripts/04_evaluate.py
```

## Estructura de directorios

```
M2-project/
├── README.md
├── requirements.txt
├── .env.example
├── data/               ← documento de FAQs (.txt)
├── logs/               ← moderation_events.jsonl (auto-generado)
├── src/m2project/
│   ├── domain/
│   │   ├── models.py       ← DTOs (FAQDocument, Chunk, RAGResponse)
│   │   ├── moderation.py   ← ModerationAction enum
│   │   └── exceptions.py   ← ContentBlockedError
│   ├── ports/
│   │   ├── llm.py          ← LLMClient protocol
│   │   ├── embedder.py     ← Embedder protocol
│   │   ├── vector_store.py ← VectorStore protocol
│   │   └── log_repository.py ← LogRepository protocol
│   ├── adapters/
│   │   ├── openai_llm.py   ← OpenAI chat completions
│   │   ├── openai_embedder.py ← OpenAI embeddings
│   │   ├── chroma_store.py ← ChromaDB
│   │   ├── text_loader.py  ← carga de .txt
│   │   └── json_log.py     ← logs de moderación en JSONL
│   ├── services/
│   │   ├── chunker.py
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   ├── pipeline.py     ← RAGPipeline (incluye validación)
│   │   └── moderation_service.py ← 3 capas de validación
│   └── factory.py
└── scripts/
    ├── 01_ingest.py    ← carga y chunkea el documento
    ├── 02_query.py     ← hace preguntas, devuelve JSON
    └── 03_evaluate.py  ← evaluador de calidad (opcional)
```

## Pendiente

- **Rate limiting**: limitar la cantidad de consultas por usuario en una ventana de tiempo para evitar uso abusivo y costos innecesarios en la API de OpenAI.
- **Reintentos con backoff**: manejar errores transitorios de la API de OpenAI (429, 5xx) con reintentos automáticos y espera creciente entre intentos.
