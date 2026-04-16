"""Structured error collection for self-healing pipeline."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from tao._io import append_jsonl, read_jsonl


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
    append_jsonl(
        Path(log_dir) / "errors.jsonl",
        {"category": category, "message": message, "details": details or {}},
    )


def read_errors(
    log_dir: str | Path,
    category: str | None = None,
) -> list[dict]:
    """Read errors from errors.jsonl, optionally filtering by category."""
    filter_fn = (lambda e: e.get("category") == category) if category else None
    return read_jsonl(Path(log_dir) / "errors.jsonl", filter_fn)


def clear_errors(log_dir: str | Path) -> None:
    """Remove all errors (fresh start after fix cycle)."""
    log_file = Path(log_dir) / "errors.jsonl"
    if log_file.exists():
        log_file.unlink()
