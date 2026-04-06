"""Structured error collection for self-healing pipeline."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


VALID_CATEGORIES = {
    "system", "experiment", "writing", "analysis",
    "planning", "pipeline", "ideation", "efficiency",
    "import", "test", "type", "state", "config", "build", "prompt",
}


def collect_error(
    log_dir: str | Path,
    category: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a structured error entry to errors.jsonl."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "category": category,
        "message": message,
        "details": details or {},
    }
    with open(log_dir / "errors.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_errors(
    log_dir: str | Path,
    category: str | None = None,
) -> list[dict]:
    """Read errors from errors.jsonl, optionally filtering by category."""
    log_file = Path(log_dir) / "errors.jsonl"
    if not log_file.exists():
        return []
    errors = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if category is None or entry.get("category") == category:
                errors.append(entry)
    return errors


def clear_errors(log_dir: str | Path) -> None:
    """Remove all errors (fresh start after fix cycle)."""
    log_file = Path(log_dir) / "errors.jsonl"
    if log_file.exists():
        log_file.unlink()
