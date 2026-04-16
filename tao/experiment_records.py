"""JSONL-based experiment database."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from tao._io import append_jsonl, read_jsonl


def record_experiment(
    workspace_root: str | Path,
    task_id: str,
    config: dict,
    results: dict,
    metrics: dict | None = None,
    metadata: dict | None = None,
) -> None:
    """Append an experiment record to experiment_db.jsonl."""
    append_jsonl(
        Path(workspace_root) / "exp" / "experiment_db.jsonl",
        {
            "task_id": task_id,
            "config": config,
            "results": results,
            "metrics": metrics or {},
            "metadata": metadata or {},
        },
    )


def load_experiments(
    workspace_root: str | Path,
    task_id: str | None = None,
) -> list[dict]:
    """Load experiment records, optionally filtered by task_id."""
    filter_fn = (lambda e: e.get("task_id") == task_id) if task_id else None
    return read_jsonl(Path(workspace_root) / "exp" / "experiment_db.jsonl", filter_fn)


def get_best_result(
    workspace_root: str | Path,
    metric_key: str,
    higher_is_better: bool = True,
) -> dict | None:
    """Find the experiment with the best value for a given metric."""
    records = load_experiments(workspace_root)
    best = None
    best_val = None
    for rec in records:
        val = rec.get("metrics", {}).get(metric_key)
        if val is None:
            continue
        if best_val is None:
            best_val = val
            best = rec
        elif higher_is_better and val > best_val:
            best_val = val
            best = rec
        elif not higher_is_better and val < best_val:
            best_val = val
            best = rec
    return best
