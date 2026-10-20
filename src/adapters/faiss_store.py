import pickle
from pathlib import Path
from typing import cast

import faiss
import numpy as np

from domain.models import Chunk, RetrievedChunk
from ports.embedder import Embedder


class FAISSStore:
    """VectorStore backed by FAISS IndexHNSWFlat with cosine similarity.

    FAISS only stores vectors — the chunks list is the parallel structure
    that maps each FAISS integer index back to its Chunk object.
    """

    def __init__(
        self,
        embedder: Embedder,
        persist_path: str = ".faiss",
        hnsw_m: int = 16,
        ef_construction: int = 200,
        ef_search: int = 50,
    ) -> None:
        self._embedder = embedder
        self._persist_path = Path(persist_path)
        self._hnsw_m = hnsw_m
        self._ef_construction = ef_construction
        self._ef_search = ef_search
        self._index: faiss.Index | None = None
        self._chunks: list[Chunk] = []
        self._load()

    # ------------------------------------------------------------------
    # VectorStore Protocol
    # ------------------------------------------------------------------

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = self._to_normalized_matrix([c.content for c in chunks])
        if self._index is None:
            self._index = self._build_index(dim=vectors.shape[1])
        self._index.add(vectors)
        self._chunks.extend(chunks)
        self._save()

    def query(self, text: str, top_k: int = 3) -> list[RetrievedChunk]:
        if self._index is None or not self._chunks:
            return []
        vector = self._to_normalized_matrix([text])
        k = min(top_k, len(self._chunks))
        distances, indices = self._index.search(vector, k)
        return [
            RetrievedChunk(chunk=self._chunks[idx], similarity=float(dist))
            for dist, idx in zip(distances[0], indices[0])
            if idx != -1
        ]

    def count(self) -> int:
        return len(self._chunks)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_index(self, dim: int) -> faiss.IndexHNSWFlat:
        # METRIC_INNER_PRODUCT + L2-normalized vectors = cosine similarity
        index = faiss.IndexHNSWFlat(dim, self._hnsw_m, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = self._ef_construction
        index.hnsw.efSearch = self._ef_search
        return index

    def _to_normalized_matrix(self, texts: list[str]) -> np.ndarray:
        vectors = np.array(self._embedder.embed(texts), dtype=np.float32)
        faiss.normalize_L2(vectors)
        return vectors

    def _save(self) -> None:
        if self._index is None:
            return
        self._persist_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._persist_path / "index.faiss"))
        with open(self._persist_path / "chunks.pkl", "wb") as f:
            pickle.dump(self._chunks, f)

    def _load(self) -> None:
        index_file = self._persist_path / "index.faiss"
        chunks_file = self._persist_path / "chunks.pkl"
        if index_file.exists() and chunks_file.exists():
            index = faiss.read_index(str(index_file))
            # faiss stubs type read_index/downcast_index as the base Index,
            # but a persisted HNSW index is an IndexHNSWFlat (has .hnsw).
            hnsw_index = cast(faiss.IndexHNSWFlat, faiss.downcast_index(index))
            hnsw_index.hnsw.efSearch = self._ef_search
            self._index = index
            with open(chunks_file, "rb") as f:
                self._chunks = pickle.load(f)
