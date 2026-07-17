from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel


class LLMClient(Protocol):
    """`.chat()` covers simple one-shot calls. `.model` exposes the
    underlying LangChain chat model so callers can compose real LCEL chains
    (prompt | model | parser) instead of hand-building strings — any
    adapter implementing this port must be backed by a LangChain chat model.
    """

    model: BaseChatModel

    def chat(self, messages: list[dict]) -> str: ...
