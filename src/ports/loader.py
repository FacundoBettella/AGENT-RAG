from typing import Protocol
from domain.models import FAQDocument


class DocumentLoader(Protocol):
    def load(self, source: str) -> list[FAQDocument]: ...
