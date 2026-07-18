from fastapi import APIRouter, HTTPException, Request

from api.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(body: IngestRequest, request: Request) -> IngestResponse:
    agents = request.app.state.agents
    agent = agents.get(body.domain)
    if agent is None:
        raise HTTPException(status_code=400, detail=f"Dominio desconocido: {body.domain}")

    chunks_indexed = agent.ingest_texts(body.documents)
    return {
        "ingest_result": {
            "domain": body.domain,
            "documents_received": len(body.documents),
            "chunks_indexed": chunks_indexed,
            "total_in_store": agent.count(),
        }
    }
