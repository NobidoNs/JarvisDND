import copy
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Callable


DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


class JsonStore:
    """Simple JSON-backed storage with naive in-process locking."""

    def __init__(self, name: str, default_factory: Callable[[], Any]):
        self.path = DATA_DIR / f"{name}.json"
        self.default_factory = default_factory
        self._lock = Lock()

    def read(self):
        with self._lock:
            if not self.path.exists():
                return self.default_factory()
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return copy.deepcopy(data)

    def write(self, data):
        with self._lock:
            tmp_path = self.path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)


def next_id(items, key: str = "id") -> int:
    """Return next integer id for a collection of dicts."""
    if not items:
        return 1
    return max(int(item.get(key, 0)) for item in items) + 1

