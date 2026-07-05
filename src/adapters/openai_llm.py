from openai import OpenAI


class OpenAILLMClient:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content or "Ha ocurrido un error inesperado. Intente más tarde."
