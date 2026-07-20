"""Langfuse tracing adapter.

`build_langchain_handler()` is the one integration point the rest of the
code needs: pass its result as `config={"callbacks": [handler]}` to any
LCEL chain's `.invoke()` and every step of that chain becomes a traced
span. A fresh handler is built per request (see Orchestrator.handle)
instead of sharing one globally, since each handler keeps its own
run-id bookkeeping and concurrent requests shouldn't share that state.
"""

from __future__ import annotations

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
