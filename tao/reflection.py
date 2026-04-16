"""Iteration logging and reflection support."""
from __future__ import annotations
import json
from pathlib import Path

from tao._io import append_jsonl, read_jsonl


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
        json.dump({"ts": __import__("time").time(), **entry}, f, indent=2, ensure_ascii=False)

    # Append to master log
    append_jsonl(log_dir / "master_log.jsonl", entry)


def load_iteration_log(workspace_root: str | Path) -> list[dict]:
    """Load the full iteration master log."""
    return read_jsonl(Path(workspace_root) / "logs" / "iterations" / "master_log.jsonl")


def get_quality_trajectory(workspace_root: str | Path) -> list[float]:
    """Extract quality scores across iterations."""
    entries = load_iteration_log(workspace_root)
    return [e["quality_score"] for e in entries if e.get("quality_score", 0) > 0]


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
