from pathlib import Path

from langchain_community.document_loaders import TextLoader as LangChainTextLoader

from domain.models import FAQDocument


class TextLoader:
    """Loads .txt documents via LangChain's TextLoader.

    `source` can be a single file or a directory; a directory loads every
    .txt file inside it as a separate FAQDocument, one per file — this is
    how each data/<domain>_docs/ knowledge base (multiple files) gets read.
    """

    def load(self, source: str) -> list[FAQDocument]:
        path = Path(source)
        files = sorted(path.glob("*.txt")) if path.is_dir() else [path]
        documents = []
        for file_path in files:
            loaded = LangChainTextLoader(str(file_path), encoding="utf-8").load()
            content = "\n\n".join(doc.page_content for doc in loaded)
            title = file_path.stem.replace("_", " ").title()
            documents.append(FAQDocument(content=content, source=str(file_path), title=title))
        return documents
