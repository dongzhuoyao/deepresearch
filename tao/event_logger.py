"""Structured event logging to JSONL files."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


def log_event(log_dir: str | Path, event_type: str, data: dict[str, Any]) -> None:
    """Append a structured event to events.jsonl in the given directory."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.time(), "type": event_type, **data}
    log_file = log_dir / "events.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_events(log_dir: str | Path, event_type: str | None = None) -> list[dict]:
    """Read events from events.jsonl, optionally filtering by type."""
    log_file = Path(log_dir) / "events.jsonl"
    if not log_file.exists():
        return []
    events = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if event_type is None or entry.get("type") == event_type:
                events.append(entry)
    return events
