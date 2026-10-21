"""Langfuse tracing adapter.

`build_langchain_handler()` is the one integration point the rest of the
code needs: pass its result as `config={"callbacks": [handler]}` to any
LCEL chain's `.invoke()` and every step of that chain becomes a traced
span. A fresh handler is built per request (see Orchestrator.handle)
instead of sharing one globally, since each handler keeps its own
run-id bookkeeping and concurrent requests shouldn't share that state.
"""

from __future__ import annotations

import os

from langfuse import get_client
from langfuse.langchain import CallbackHandler


def build_langchain_handler() -> CallbackHandler:
    return CallbackHandler()


def push_evaluation_score(trace_id: str | None, eval_result: dict) -> None:
    """Push the LLM-as-judge score (services/evaluator.py) to Langfuse's
    Score API, attached to the trace it evaluated -- the bonus mentioned in
    ADR-011. No-op if tracing isn't configured (`trace_id` is None) or the
    evaluator's response didn't parse (see `evaluate_response`'s
    `{"error": ...}` fallback, which has no "score" key).
    """
    if trace_id is None or "score" not in eval_result:
        return
    get_client().create_score(
        trace_id=trace_id,
        name="llm_as_judge",
        data_type="NUMERIC",
        value=eval_result["score"],
        comment=eval_result.get("justificacion"),
    )


def is_tracing_enabled() -> bool:
    """Whether Langfuse will actually record anything: both API keys are set
    and tracing wasn't switched off via LANGFUSE_TRACING_ENABLED=false. The
    SDK has no public flag for this, so mirror the conditions it checks.
    """
    if os.environ.get("LANGFUSE_TRACING_ENABLED", "true").lower() == "false":
        return False
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def push_user_feedback(trace_id: str, helpful: bool) -> None:
    get_client().create_score(
        trace_id=trace_id,
        name="user_feedback",
        data_type="BOOLEAN",
        value=int(helpful),
        score_id=f"user_feedback-{trace_id}",
    )
