"""JSONL-based experiment database."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


def record_experiment(
    workspace_root: str | Path,
    task_id: str,
    config: dict,
    results: dict,
    metrics: dict | None = None,
    metadata: dict | None = None,
) -> None:
    """Append an experiment record to experiment_db.jsonl."""
    db_file = Path(workspace_root) / "exp" / "experiment_db.jsonl"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "task_id": task_id,
        "config": config,
        "results": results,
        "metrics": metrics or {},
        "metadata": metadata or {},
    }
    with open(db_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_experiments(
    workspace_root: str | Path,
    task_id: str | None = None,
) -> list[dict]:
    """Load experiment records, optionally filtered by task_id."""
    db_file = Path(workspace_root) / "exp" / "experiment_db.jsonl"
    if not db_file.exists():
        return []
    records = []
    with open(db_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if task_id is None or entry.get("task_id") == task_id:
                records.append(entry)
    return records


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
