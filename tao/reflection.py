"""Iteration logging and reflection support."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


def log_iteration(
    workspace_root: str | Path,
    iteration: int,
    stage: str,
    changes: str,
    issues_found: int,
    issues_fixed: int,
    quality_score: float,
    notes: str = "",
) -> None:
    """Log an iteration event to the master log."""
    workspace_root = Path(workspace_root)
    log_dir = workspace_root / "logs" / "iterations"
    log_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": time.time(),
        "iteration": iteration,
        "stage": stage,
        "changes": changes,
        "issues_found": issues_found,
        "issues_fixed": issues_fixed,
        "quality_score": quality_score,
        "notes": notes,
    }

    # Write per-iteration file
    iter_file = log_dir / f"iter_{iteration:03d}_{stage}.json"
    with open(iter_file, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)

    # Append to master log
    master_log = log_dir / "master_log.jsonl"
    with open(master_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_iteration_log(workspace_root: str | Path) -> list[dict]:
    """Load the full iteration master log."""
    master_log = Path(workspace_root) / "logs" / "iterations" / "master_log.jsonl"
    if not master_log.exists():
        return []
    entries = []
    with open(master_log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def get_quality_trajectory(workspace_root: str | Path) -> list[float]:
    """Extract quality scores across iterations."""
    entries = load_iteration_log(workspace_root)
    scores = []
    for entry in entries:
        score = entry.get("quality_score")
        if score is not None and score > 0:
            scores.append(score)
    return scores


def assess_trajectory(scores: list[float]) -> str:
    """Assess quality trajectory: improving, stagnant, or declining."""
    if len(scores) < 2:
        return "insufficient_data"
    recent = scores[-3:] if len(scores) >= 3 else scores
    if all(recent[i] >= recent[i - 1] for i in range(1, len(recent))):
        return "improving"
    if all(recent[i] <= recent[i - 1] for i in range(1, len(recent))):
        return "declining"
    return "stagnant"
