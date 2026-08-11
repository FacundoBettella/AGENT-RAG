from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

load_dotenv()

from agents import finance_agent, hr_agent, tech_agent
from agents.orchestrator import build_orchestrator
from api.exception_handlers import register_handlers
from api.routes import evaluate, health, ingest, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el orquestador y el registro de agentes de dominio una
    sola vez al arrancar el servidor. Los agentes ingestan su knowledge
    base perezosamente, en la primera consulta que les llega.
    """
    app.state.orchestrator = build_orchestrator()
    app.state.agents = {
        "hr": hr_agent.agent,
        "tech": tech_agent.agent,
        "finance": finance_agent.agent,
    }
    yield


app = FastAPI(
    title="Multi-Agent Support Router API",
    description="Orquestador + RAG agents especializados (HR/Tech/Finance) para soporte interno",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")

register_handlers(app)


@app.get("/scalar", include_in_schema=False)
def scalar_docs():
    """Postman-like interactive API client, alternative to Swagger UI (/docs)."""
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
