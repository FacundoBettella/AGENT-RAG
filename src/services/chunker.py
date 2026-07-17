from langchain_text_splitters import RecursiveCharacterTextSplitter

from domain.models import Chunk, FAQDocument


class Chunker:
    """Wraps LangChain's RecursiveCharacterTextSplitter.

    Splits hierarchically (paragraph -> sentence -> word -> char), falling
    back to the next separator only when a chunk doesn't fit — a more robust
    strategy than a single "\\n\\n" soft-break heuristic for documents whose
    section/paragraph lengths vary a lot, like these per-domain FAQs.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size debe ser positivo")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe estar en [0, chunk_size)")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, document: FAQDocument) -> list[Chunk]:
        texts = self._splitter.split_text(document.content)
        return [
            Chunk(
                content=text.strip(),
                document_id=document.id,
                chunk_index=index,
                metadata={"source": document.source, "title": document.title},
            )
            for index, text in enumerate(texts)
        ]

    def split_many(self, documents: list[FAQDocument]) -> list[Chunk]:
        return [chunk for doc in documents for chunk in self.split(doc)]
