# Sistema Multi-Agente de Soporte Interno (HR / IT / Finance)

Un **Agente Orquestador** clasifica la intención de una consulta de empleado y la enruta,
de forma condicional, al **Agente RAG especializado** correspondiente (HR, IT/Tech o
Finanzas). Incluye moderación pre-LLM y un evaluador automático (LLM-as-judge) que puntúa
cada respuesta.

Más detalle técnico: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (cómo está armado) y
[`docs/DECISIONS.md`](docs/DECISIONS.md) (por qué se tomó cada decisión).

## Alcance

Responde preguntas de empleados en 3 dominios, contra una knowledge base de ejemplo
(`data/`) de una SaaS company ficticia. Con `docker compose exec app python
scripts/02_query.py "<pregunta>"` o vía `/api/query` podés preguntar cosas como:

| Dominio | Ejemplos de lo que sabe responder |
|---|---|
| **HR** | Sueldos y liquidación, vacaciones y licencias, modalidad de trabajo (remoto/híbrido), beneficios, equity, relocation, promociones, onboarding/desvinculación, código de conducta, acoso y discriminación, bienestar y salud mental |
| **IT / Tech** | Contraseñas y autenticación, VPN y acceso remoto, instalación de software, seguridad e incidentes, accesos a repos/CI-CD, entornos de desarrollo, hardware y periféricos, BYOD, herramientas aprobadas, mesa de ayuda |
| **Finance** | Rendición de gastos, tarjeta corporativa, viajes corporativos, procurement y pago a proveedores, presupuesto por área, cierre contable, facturación a clientes, régimen impositivo, auditorías |

Lo que **no** hace (a propósito, ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#limitaciones-conocidas)):

- Preguntas fuera de esos 3 dominios (Legal, Ventas, etc.) → responde "fuera de alcance", no inventa una respuesta.
- Preguntas compuestas que cruzan dos dominios a la vez → elige un solo dominio, no las divide.
- Memoria conversacional → cada pregunta se resuelve sola, sin contexto de preguntas anteriores.
- No está conectado a sistemas reales (HRIS, ITSM, ERP) — la knowledge base son `.txt` de ejemplo, pensados para mostrar el patrón de arquitectura, no para producción tal cual.

## Tecnologías

| Componente | Uso |
|---|---|
| **LangChain** (`langchain-core`, `langchain-openai`, `langchain-chroma`) | Chains LCEL (`prompt \| llm \| parser`), structured output, integración con Chroma. LangChain 1.x — LCEL puro, no `create_agent`. |
| **OpenAI** | Chat (`gpt-4o-mini`) para clasificación, generación y evaluación; `text-embedding-3-small` para embeddings. |
| **ChromaDB** | Vector store primario, multi-colección (una por dominio). |
| **Langfuse v4** (OTel-based) | Tracing end-to-end + Score API para el evaluador. |
| **FastAPI** | Expone el orquestador por HTTP. |
| **Pydantic** | Schema de clasificación estructurada y modelos de la API. |
| **Docker / Docker Compose** | Entorno de desarrollo — no hace falta Python ni venv local. |

## Setup

```bash
cp .env.example .env              # completar OPENAI_API_KEY como mínimo
docker compose up --build
```

La API queda en `http://localhost:8080`, con reload automático.

Completar en `.env`:

| Variable | Descripción | Default |
|---|---|---|
| `OPENAI_API_KEY` | API key de OpenAI | — |
| `LOG_HASH_SALT` | Salt para hashear inputs en logs de moderación | `m2-default-salt-change-me` |
| `LOGS_DIR` | Carpeta de logs de moderación | `logs` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Keys de tu proyecto en [cloud.langfuse.com](https://cloud.langfuse.com) (cuenta gratuita) | — (sin esto, tracing se desactiva solo) |
| `LANGFUSE_BASE_URL` | Región de Langfuse Cloud | `https://cloud.langfuse.com` |

## Endpoints

| Endpoint | Qué hace |
|---|---|
| `POST /api/query` | Pregunta → orquestador → intent + respuesta + chunks |
| `POST /api/evaluate` | Igual que `/query` + score del LLM-as-judge (empujado a Langfuse) |
| `POST /api/ingest` | Agrega documentos a un dominio |
| `GET /api/health` | Chunks indexados por colección |
| `GET /docs` | Swagger UI (autogenerado por FastAPI) |
| `GET /scalar` | Scalar — UI alternativa a Swagger, con un cliente "try it out" al estilo Postman |

## Scripts y notebook

`scripts/*.py` corren dentro del container (`docker compose exec app python scripts/...`):
`01_ingest`, `02_query "<pregunta>"`, `03_evaluate "<pregunta>"`, `05_test_routing` (corre
`test_queries.json`, 21 casos, contra el orquestador).

`multi_agent_system.ipynb` necesita un entorno Python local (`pip install -r
requirements.txt`) — Jupyter no corre dentro del container.
