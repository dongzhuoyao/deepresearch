"""Dashboard data generation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def get_dashboard_data(workspace_root: str | Path) -> dict:
    """Generate comprehensive dashboard data for a workspace."""
    root = Path(workspace_root)

    # Status
    status = _load_json(root / "status.json") or {"stage": "unknown", "iteration": 0}

    # Experiment progress
    progress = _load_json(root / "exp" / "gpu_progress.json") or {"running": {}, "completed": []}

    # Experiment state
    exp_state = _load_json(root / "exp" / "experiment_state.json") or {"tasks": {}}

    # Task plan
    task_plan = _load_json(root / "plan" / "task_plan.json") or {"tasks": []}

    # Quality trajectory
    quality_scores = _load_quality_scores(root)

    return {
        "status": status,
        "experiment_progress": {
            "total": len(task_plan.get("tasks", [])),
            "completed": len(progress.get("completed", [])),
            "running": len(progress.get("running", {})),
        },
        "experiment_state": {
            "tasks": len(exp_state.get("tasks", {})),
            "recovery_events": len(exp_state.get("recovery_log", [])),
        },
        "quality_scores": quality_scores,
        "has_paper": (root / "writing" / "paper.md").exists(),
        "has_latex": (root / "writing" / "latex" / "paper.pdf").exists(),
    }


def list_all_projects(workspaces_dir: str | Path) -> list[dict]:
    """List all projects with basic status."""
    base = Path(workspaces_dir)
    if not base.exists():
        return []
    projects = []
    for status_file in sorted(base.glob("*/status.json")):
        data = _load_json(status_file) or {}
        projects.append({
            "name": status_file.parent.name,
            "path": str(status_file.parent),
            "stage": data.get("stage", "unknown"),
            "iteration": data.get("iteration", 0),
        })
    return projects


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_quality_scores(root: Path) -> list[float]:
    master_log = root / "logs" / "iterations" / "master_log.jsonl"
    if not master_log.exists():
        return []
    scores = []
    with open(master_log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                score = entry.get("quality_score")
                if score and score > 0:
                    scores.append(score)
            except json.JSONDecodeError:
                pass
    return scores
