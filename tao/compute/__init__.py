"""Compute backend registry."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.config import Config
    from tao.compute.base import ComputeBackend


def get_backend(config: "Config", workspace_active_root: str = "") -> "ComputeBackend":
    """Get the compute backend based on config."""
    from tao.compute.runpod_backend import RunPodBackend
    return RunPodBackend.from_config(config, workspace_active_root)
