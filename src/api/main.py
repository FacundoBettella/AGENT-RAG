from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from m2project.api.exception_handlers import register_handlers
from m2project.api.routes import evaluate, health, ingest, query
from m2project.factory import build_faq_bundle


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el bundle una sola vez al arrancar el servidor."""
    app.state.bundle = build_faq_bundle()
    yield


app = FastAPI(
    title="FAQ Chatbot API",
    description="RAG system para soporte interno de HR SaaS",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")

register_handlers(app)
