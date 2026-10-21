from fastapi import APIRouter, HTTPException

from adapters.tracing import is_tracing_enabled, push_user_feedback
from api.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
def post_feedback(body: FeedbackRequest) -> FeedbackResponse:
    if not is_tracing_enabled():
        raise HTTPException(
            status_code=503, detail="Tracing deshabilitado: el feedback no se registró"
        )
    push_user_feedback(body.trace_id, body.helpful)
    return FeedbackResponse.model_validate(
        {"feedback_result": {"trace_id": body.trace_id, "helpful": body.helpful}}
    )
