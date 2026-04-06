"""Rebuttal workspace setup."""
from __future__ import annotations
from pathlib import Path


def setup_rebuttal_workspace(workspace_root: str | Path) -> Path:
    """Create rebuttal directory structure in workspace."""
    root = Path(workspace_root)
    rebuttal_dir = root / "rebuttal"

    dirs = [
        "reviews",       # Original reviewer comments
        "strategy",      # Rebuttal strategy docs
        "drafts",        # Rebuttal draft iterations
        "simulated",     # Simulated reviewer feedback
        "scores",        # Score history
        "final",         # Final rebuttal
    ]
    for d in dirs:
        (rebuttal_dir / d).mkdir(parents=True, exist_ok=True)

    return rebuttal_dir
