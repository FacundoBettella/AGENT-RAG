from m2project.domain.models import Chunk, FAQDocument


class Chunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size debe ser positivo")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe estar en [0, chunk_size)")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, document: FAQDocument) -> list[Chunk]:
        text = document.content
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            window = text[start:end]

            # intenta cortar en un salto de párrafo para no partir oraciones
            if end < len(text):
                soft_break = window.rfind("\n\n")
                if soft_break != -1 and soft_break > self.chunk_size // 2:
                    end = start + soft_break
                    window = text[start:end]

            chunks.append(Chunk(
                content=window.strip(),
                document_id=document.id,
                chunk_index=index,
                metadata={"source": document.source, "title": document.title},
            ))
            index += 1

            if end >= len(text):
                break
            start = end - self.chunk_overlap

        return chunks

    def split_many(self, documents: list[FAQDocument]) -> list[Chunk]:
        return [chunk for doc in documents for chunk in self.split(doc)]
