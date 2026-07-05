from typing import Protocol
from m2project.domain.models import FAQDocument


class DocumentLoader(Protocol):
    def load(self, source: str) -> list[FAQDocument]: ...
