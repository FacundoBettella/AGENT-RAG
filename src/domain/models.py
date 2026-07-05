from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class FAQDocument:
    content: str
    source: str
    title: str
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Chunk:
    content: str
    document_id: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    similarity: float


@dataclass(frozen=True)
class RAGResponse:
    user_question: str
    system_answer: str
    chunks_related: list[RetrievedChunk]

    def to_dict(self) -> dict:
        return {
            "user_question": self.user_question,
            "system_answer": self.system_answer,
            "chunks_related": [
                {
                    "content": rc.chunk.content,
                    "source": rc.chunk.metadata.get("source", rc.chunk.document_id),
                    "similarity": round(rc.similarity, 4),
                }
                for rc in self.chunks_related
            ],
        }
