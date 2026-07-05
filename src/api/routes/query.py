from fastapi import APIRouter, Request

from m2project.api.schemas import QueryResponse, QuestionRequest

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def post_query(body: QuestionRequest, request: Request) -> QueryResponse:
    bundle = request.app.state.bundle
    response = bundle.pipeline.ask(body.question)
    return {"query_result": response.to_dict()}
