from typing import Any, Protocol


class LogRepository(Protocol):
    def write_log(self, record: dict[str, Any]) -> None: ...
