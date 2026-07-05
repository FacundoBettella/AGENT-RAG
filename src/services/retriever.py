from m2project.domain.models import RetrievedChunk
from m2project.ports.vector_store import VectorStore


class Retriever:
    def __init__(self, store: VectorStore, top_k: int = 3) -> None:
        self._store = store
        self._top_k = top_k

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        return self._store.query(text=question, top_k=self._top_k)
