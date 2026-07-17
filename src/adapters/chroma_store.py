from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from domain.models import Chunk, RetrievedChunk
from ports.embedder import Embedder


class ChromaStore:
    """VectorStore Protocol implementation backed by langchain_chroma.Chroma
    (ChromaDB's HNSW index under the hood).

    Converts between our own Chunk/RetrievedChunk domain objects and
    LangChain's Document at this boundary, so the rest of the app (Indexer,
    Retriever, RAGPipeline) never has to import a LangChain type directly —
    LangChain is an implementation detail of this adapter, not a leak into
    the domain/services layers.
    """

    def __init__(
        self,
        embedder: Embedder,
        collection_name: str = "faq",
        persist_directory: str = ".chroma",
    ) -> None:
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self._store = Chroma(
            collection_name=collection_name,
            embedding_function=embedder,
            persist_directory=persist_directory,
            # explicit cosine space so similarity_search_with_relevance_scores
            # has a defined score function (defaults to L2 otherwise).
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        documents = [
            Document(
                page_content=c.content,
                metadata={"document_id": c.document_id, "chunk_index": c.chunk_index, **c.metadata},
            )
            for c in chunks
        ]
        self._store.add_documents(documents, ids=[c.id for c in chunks])

    def query(self, text: str, top_k: int = 3) -> list[RetrievedChunk]:
        results = self._store.similarity_search_with_relevance_scores(text, k=top_k)
        retrieved = []
        for doc, score in results:
            meta = dict(doc.metadata or {})
            chunk = Chunk(
                content=doc.page_content,
                document_id=str(meta.pop("document_id", "")),
                chunk_index=int(meta.pop("chunk_index", 0)),
                metadata=meta,
            )
            retrieved.append(RetrievedChunk(chunk=chunk, similarity=float(score)))
        return retrieved

    def count(self) -> int:
        return self._store._collection.count()
