from typing import Any

import pytest

from adapters import tracing

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
OTHER_TRACE_ID = "00000000000000000000000000000001"


class FakeLangfuseClient:
    def __init__(self) -> None:
        self.scores: list[dict[str, Any]] = []

    def create_score(self, **kwargs: Any) -> None:
        self.scores.append(kwargs)


@pytest.fixture
def langfuse_client(monkeypatch: pytest.MonkeyPatch) -> FakeLangfuseClient:
    fake = FakeLangfuseClient()
    monkeypatch.setattr(tracing, "get_client", lambda: fake)
    return fake


def test_helpful_feedback_creates_boolean_score_with_value_1(
    langfuse_client: FakeLangfuseClient,
) -> None:
    tracing.push_user_feedback(TRACE_ID, True)

    assert len(langfuse_client.scores) == 1
    score = langfuse_client.scores[0]
    assert score["trace_id"] == TRACE_ID
    assert score["name"] == "user_feedback"
    assert score["data_type"] == "BOOLEAN"
    assert score["value"] == 1
    assert isinstance(score["score_id"], str) and score["score_id"]


def test_not_helpful_feedback_creates_boolean_score_with_value_0(
    langfuse_client: FakeLangfuseClient,
) -> None:
    tracing.push_user_feedback(TRACE_ID, False)

    score = langfuse_client.scores[0]
    assert score["name"] == "user_feedback"
    assert score["data_type"] == "BOOLEAN"
    assert score["value"] == 0


def test_revote_reuses_the_score_id_so_langfuse_overwrites_the_previous_vote(
    langfuse_client: FakeLangfuseClient,
) -> None:
    tracing.push_user_feedback(TRACE_ID, True)
    tracing.push_user_feedback(TRACE_ID, False)

    first, second = langfuse_client.scores
    assert first["score_id"] == second["score_id"]
    assert (first["value"], second["value"]) == (1, 0)


def test_different_traces_get_different_score_ids(langfuse_client: FakeLangfuseClient) -> None:
    tracing.push_user_feedback(TRACE_ID, True)
    tracing.push_user_feedback(OTHER_TRACE_ID, True)

    first, second = langfuse_client.scores
    assert first["score_id"] != second["score_id"]


@pytest.fixture
def langfuse_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.delenv("LANGFUSE_TRACING_ENABLED", raising=False)
    return monkeypatch


def test_tracing_is_enabled_when_both_keys_are_configured(
    langfuse_env: pytest.MonkeyPatch,
) -> None:
    assert tracing.is_tracing_enabled() is True


@pytest.mark.parametrize("missing_key", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"])
def test_tracing_is_disabled_when_a_key_is_missing(
    langfuse_env: pytest.MonkeyPatch, missing_key: str
) -> None:
    langfuse_env.delenv(missing_key)

    assert tracing.is_tracing_enabled() is False


def test_tracing_is_disabled_when_explicitly_turned_off(
    langfuse_env: pytest.MonkeyPatch,
) -> None:
    langfuse_env.setenv("LANGFUSE_TRACING_ENABLED", "false")

    assert tracing.is_tracing_enabled() is False
