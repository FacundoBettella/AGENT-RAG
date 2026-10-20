from pathlib import Path

from adapters.faiss_store import FAISSStore
from domain.models import Chunk

_VOCAB = ["vacaciones", "vpn", "reembolso"]


class BagOfWordsEmbedder:
    """Deterministic embedder: one dimension per vocabulary word."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(word in text.lower()) + 0.01 for word in _VOCAB] for text in texts]


def _chunks() -> list[Chunk]:
    return [
        Chunk(content="Pedir vacaciones", document_id="d1", chunk_index=0),
        Chunk(content="Configurar la VPN", document_id="d2", chunk_index=0),
        Chunk(content="Solicitar reembolso", document_id="d3", chunk_index=0),
    ]


def test_query_on_empty_store_returns_nothing(tmp_path: Path) -> None:
    store = FAISSStore(BagOfWordsEmbedder(), persist_path=str(tmp_path))

    assert store.count() == 0
    assert store.query("vpn") == []


def test_add_then_query_returns_most_similar_chunk(tmp_path: Path) -> None:
    store = FAISSStore(BagOfWordsEmbedder(), persist_path=str(tmp_path))
    store.add(_chunks())

    results = store.query("vpn", top_k=1)

    assert store.count() == 3
    assert [r.chunk.content for r in results] == ["Configurar la VPN"]


def test_persisted_index_is_reloaded_and_searchable(tmp_path: Path) -> None:
    FAISSStore(BagOfWordsEmbedder(), persist_path=str(tmp_path)).add(_chunks())

    reloaded = FAISSStore(BagOfWordsEmbedder(), persist_path=str(tmp_path), ef_search=20)

    assert reloaded.count() == 3
    assert reloaded.query("reembolso", top_k=1)[0].chunk.content == "Solicitar reembolso"


def test_add_empty_list_does_not_persist_anything(tmp_path: Path) -> None:
    store = FAISSStore(BagOfWordsEmbedder(), persist_path=str(tmp_path / "idx"))

    store.add([])

    assert not (tmp_path / "idx").exists()
