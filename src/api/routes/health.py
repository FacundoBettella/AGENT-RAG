from fastapi import APIRouter, Request

from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    agents = request.app.state.agents
    chunks_indexed = {name: agent.count() for name, agent in agents.items()}
    return HealthResponse(status="ok", chunks_indexed=chunks_indexed)
