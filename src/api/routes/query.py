from fastapi import APIRouter, Request

from api.schemas import QueryResponse, QuestionRequest

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def post_query(body: QuestionRequest, request: Request) -> QueryResponse:
    orchestrator = request.app.state.orchestrator
    result = orchestrator.handle(body.question)
    return QueryResponse.model_validate(
        {
            "query_result": {
                **result.rag_response.to_dict(),
                "intent": result.intent,
                "reasoning": result.reasoning,
                "trace_id": result.trace_id,
            }
        }
    )
