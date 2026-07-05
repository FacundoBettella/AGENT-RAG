from pathlib import Path

from m2project.domain.models import FAQDocument


class TextLoader:
    def load(self, source: str) -> list[FAQDocument]:
        path = Path(source)
        content = path.read_text(encoding="utf-8")
        title = path.stem.replace("_", " ").title()
        return [FAQDocument(content=content, source=source, title=title)]
