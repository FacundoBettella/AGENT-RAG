from langchain_openai import OpenAIEmbeddings


class OpenAIEmbedder:
    """Wraps langchain_openai.OpenAIEmbeddings.

    `.embed()` satisfies our own Embedder port (used by services that don't
    know about LangChain). `.embed_documents()` / `.embed_query()` are also
    exposed so this same instance can be passed directly as the
    `embedding_function` of a LangChain vector store (e.g. Chroma) without
    creating a second embeddings object.
    """

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        self._model = OpenAIEmbeddings(model=model, api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)
