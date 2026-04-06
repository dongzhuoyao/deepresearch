"""Rebuttal CLI commands."""
from __future__ import annotations
import json
from pathlib import Path


def cli_rebuttal_init(workspace_path: str, reviews_path: str) -> str:
    """Initialize rebuttal from reviews JSON file."""
    from tao.rebuttal.orchestrator import RebuttalOrchestrator
    reviews = json.loads(Path(reviews_path).read_text())
    orch = RebuttalOrchestrator(workspace_path)
    stage = orch.init(reviews)
    return json.dumps({"stage": stage, "workspace": workspace_path})


def cli_rebuttal_status(workspace_path: str) -> str:
    """Get rebuttal pipeline status."""
    from tao.rebuttal.orchestrator import RebuttalOrchestrator
    orch = RebuttalOrchestrator(workspace_path)
    return json.dumps(orch.get_status(), indent=2)
