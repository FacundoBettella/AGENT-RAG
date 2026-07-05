from pathlib import Path

import chromadb
from chromadb.config import Settings

from m2project.domain.models import Chunk, RetrievedChunk
from m2project.ports.embedder import Embedder


class ChromaStore:
    def __init__(
        self,
        embedder: Embedder,
        collection_name: str = "faq",
        persist_directory: str = ".chroma",
    ) -> None:
        self._embedder = embedder
        path = Path(persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        texts = [c.content for c in chunks]
        embeddings = self._embedder.embed(texts)
        self._collection.add(
            ids=[c.id for c in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {"document_id": c.document_id, "chunk_index": c.chunk_index, **c.metadata}
                for c in chunks
            ],
        )

    def query(self, text: str, top_k: int = 3) -> list[RetrievedChunk]:
        embedding = self._embedder.embed([text])[0]
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]

        retrieved = []
        for doc, meta, dist, cid in zip(documents, metadatas, distances, ids):
            meta = dict(meta or {})
            chunk = Chunk(
                id=str(cid),
                content=str(doc),
                document_id=str(meta.pop("document_id", cid)),
                chunk_index=int(meta.pop("chunk_index", 0)),
                metadata=meta,
            )
            similarity = 1 - float(dist)
            retrieved.append(RetrievedChunk(chunk=chunk, similarity=similarity))
        return retrieved

    def count(self) -> int:
        return self._collection.count()
