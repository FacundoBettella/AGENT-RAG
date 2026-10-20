import os

from fastapi import APIRouter, Request

from adapters.openai_llm import OpenAILLMClient
from adapters.tracing import push_evaluation_score
from api.schemas import EvaluateResponse, QuestionRequest
from services.evaluator import evaluate_response

router = APIRouter()

_evaluator_llm: OpenAILLMClient | None = None


def _get_evaluator_llm() -> OpenAILLMClient:
    global _evaluator_llm
    if _evaluator_llm is None:
        _evaluator_llm = OpenAILLMClient(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    return _evaluator_llm


@router.post("/evaluate", response_model=EvaluateResponse)
def post_evaluate(body: QuestionRequest, request: Request) -> EvaluateResponse:
    orchestrator = request.app.state.orchestrator
    result = orchestrator.handle(body.question)
    response = result.rag_response

    evaluation = evaluate_response(_get_evaluator_llm(), response)
    push_evaluation_score(result.trace_id, evaluation)

    eval_result = response.to_dict()
    eval_result["intent"] = result.intent
    eval_result["evaluation"] = evaluation
    return EvaluateResponse.model_validate({"evaluate_result": eval_result})
