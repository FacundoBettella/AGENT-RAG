from fastapi import APIRouter, Request

from m2project.api.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(body: IngestRequest, request: Request) -> IngestResponse:
    bundle = request.app.state.bundle
    chunks_indexed = bundle.indexer.index_texts(body.documents)
    return {
        "ingest_result": {
            "documents_received": len(body.documents),
            "chunks_indexed": chunks_indexed,
            "total_in_store": bundle.indexer._store.count(),
        }
    }
