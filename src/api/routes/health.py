from fastapi import APIRouter, Request

from m2project.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    bundle = request.app.state.bundle
    return HealthResponse(
        status="ok",
        chunks_indexed=bundle.indexer._store.count(),
    )
