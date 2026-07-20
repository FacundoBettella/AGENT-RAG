from langchain_openai import ChatOpenAI


class OpenAILLMClient:
    """Wraps langchain_openai.ChatOpenAI.

    `.chat()` satisfies our own LLMClient port for simple one-shot calls
    (e.g. the orchestrator's classification step). `.model` exposes the
    underlying ChatOpenAI instance so RAGPipeline can compose it into a real
    LCEL chain (prompt | model | parser) instead of building strings by hand.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self.model = ChatOpenAI(model=model, api_key=api_key, temperature=temperature)

    def chat(self, messages: list[dict]) -> str:
        response = self.model.invoke(messages)
        return response.content or "Ha ocurrido un error inesperado. Intente más tarde."
