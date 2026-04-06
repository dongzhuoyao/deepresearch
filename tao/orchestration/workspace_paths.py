"""Workspace path resolution helpers."""
from __future__ import annotations
from pathlib import Path


def resolve_active_root(workspace_root: Path, iteration_dirs: bool, iteration: int) -> Path:
    """Return the active working directory for the current iteration.

    If iteration_dirs is True, returns workspace_root/iter_NNN/.
    Otherwise returns workspace_root directly.
    """
    if not iteration_dirs or iteration < 1:
        return workspace_root
    iter_dir = workspace_root / f"iter_{iteration:03d}"
    return iter_dir


def ensure_workspace_dirs(active_root: Path) -> None:
    """Create standard workspace subdirectories if they don't exist."""
    dirs = [
        "idea", "idea/perspectives", "idea/debate", "idea/result_debate",
        "plan",
        "exp", "exp/code", "exp/results", "exp/results/pilots", "exp/results/full", "exp/logs",
        "writing", "writing/sections", "writing/critique", "writing/figures", "writing/latex",
        "context",
        "supervisor",
        "reflection",
        "logs", "logs/iterations", "logs/stage_summaries",
        "lark_sync",
    ]
    for d in dirs:
        (active_root / d).mkdir(parents=True, exist_ok=True)


def project_path(workspace_root: Path, relative: str) -> Path:
    """Get project-scoped path (preserved across iterations)."""
    return workspace_root / relative


def active_path(active_root: Path, relative: str) -> Path:
    """Get iteration-scoped path (cleared between iterations)."""
    return active_root / relative
