"""Central path resolution for the Tao system."""
from __future__ import annotations
from pathlib import Path
import os


def tao_root() -> Path:
    """Return the Tao system root (repo checkout).

    Uses TAO_ROOT env var if set, otherwise derives from this file's location.
    """
    env = os.environ.get("TAO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def system_data_dir() -> Path:
    """Return ~/.tao/ for cross-project persistent data."""
    return Path.home() / ".tao"


def prompts_dir() -> Path:
    """Return the directory containing prompt templates."""
    return Path(__file__).resolve().parent / "prompts"


def global_config_path() -> Path:
    """Return ~/.tao/config.yaml path."""
    return system_data_dir() / "config.yaml"
