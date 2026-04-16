"""Structured event logging to JSONL files."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from tao._io import append_jsonl, read_jsonl


def log_event(log_dir: str | Path, event_type: str, data: dict[str, Any]) -> None:
    """Append a structured event to events.jsonl in the given directory."""
    append_jsonl(Path(log_dir) / "events.jsonl", {"type": event_type, **data})


def read_events(log_dir: str | Path, event_type: str | None = None) -> list[dict]:
    """Read events from events.jsonl, optionally filtering by type."""
    filter_fn = (lambda e: e.get("type") == event_type) if event_type else None
    return read_jsonl(Path(log_dir) / "events.jsonl", filter_fn)
