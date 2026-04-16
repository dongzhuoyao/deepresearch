"""Shared I/O utilities for JSONL and atomic JSON operations."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Callable


def append_jsonl(path: str | Path, entry: dict[str, Any], *, auto_ts: bool = True) -> None:
    """Append a single JSON entry to a JSONL file, creating parent dirs as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if auto_ts and "ts" not in entry:
        entry = {"ts": time.time(), **entry}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_jsonl(
    path: str | Path,
    filter_fn: Callable[[dict], bool] | None = None,
) -> list[dict]:
    """Read all entries from a JSONL file, optionally filtering."""
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as f:
            entries = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if filter_fn is None or filter_fn(entry):
                    entries.append(entry)
            return entries
    except FileNotFoundError:
        return []


def atomic_write_json(path: str | Path, data: Any) -> None:
    """Write JSON atomically via tmp-file swap."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(path)
