from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class JsonStorage:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.file_path.exists():
            self.save(
                {
                    "mailboxes": [],
                    "meta": {
                        "created_mailbox_count": 0,
                        "last_mailbox_created_at": None,
                        "last_sync_at": None,
                    },
                }
            )

    def load(self) -> dict[str, Any]:
        with self._lock:
            with self.file_path.open("r", encoding="utf-8") as fp:
                return json.load(fp)

    def save(self, payload: dict[str, Any]) -> None:
        with self._lock:
            with self.file_path.open("w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self.load())

    def update(self, mutator):
        with self._lock:
            with self.file_path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
            mutator(payload)
            with self.file_path.open("w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
            return deepcopy(payload)
