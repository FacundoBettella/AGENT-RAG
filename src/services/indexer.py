from domain.models import FAQDocument
from ports.loader import DocumentLoader
from ports.vector_store import VectorStore
from services.chunker import Chunker


class Indexer:
    def __init__(self, loader: DocumentLoader, chunker: Chunker, store: VectorStore) -> None:
        self._loader = loader
        self._chunker = chunker
        self._store = store

    def index(self, source: str) -> int:
        documents = self._loader.load(source)
        chunks = self._chunker.split_many(documents)
        self._store.add(chunks)
        return len(chunks)

    def index_texts(self, texts: list[str]) -> int:
        documents = [
            FAQDocument(content=text, source="api", title=f"document-{i}")
            for i, text in enumerate(texts)
        ]
        chunks = self._chunker.split_many(documents)
        self._store.add(chunks)
        return len(chunks)
