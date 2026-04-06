"""Monitor API for experiment status."""
from __future__ import annotations
from pathlib import Path

from tao.gpu_scheduler import get_progress_summary
from tao.experiment_recovery import get_experiment_summary


def get_experiment_status(workspace_root: str | Path) -> dict:
    """Get combined experiment status."""
    return {
        "progress": get_progress_summary(workspace_root),
        "state": get_experiment_summary(workspace_root),
    }
