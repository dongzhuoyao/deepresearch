"""Core CLI helpers shared across sub-CLIs."""
from __future__ import annotations
from pathlib import Path


def resolve_workspace(path: str = ".") -> Path:
    """Resolve a workspace path, handling '.' and relative paths."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Workspace not found: {p}")
    return p


def find_workspaces(base_dir: str = "workspace") -> list[Path]:
    """Find all workspaces under a base directory."""
    base = Path(base_dir)
    if not base.exists():
        return []
    return sorted([
        p.parent for p in base.glob("*/status.json")
    ])
