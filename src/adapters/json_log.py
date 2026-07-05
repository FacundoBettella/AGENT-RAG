import json
from pathlib import Path
from typing import Any


class JsonLogRepository:
    def __init__(self, logs_dir: str = "logs") -> None:
        self._path = Path(logs_dir)
        self._path.mkdir(exist_ok=True)

    def write_log(self, record: dict[str, Any]) -> None:
        log_file = self._path / "moderation_events.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
