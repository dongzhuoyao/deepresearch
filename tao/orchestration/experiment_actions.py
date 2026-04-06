"""Experiment action builders for GPU-parallel stages."""
from __future__ import annotations
from typing import TYPE_CHECKING
from tao.orchestration.models import Action

if TYPE_CHECKING:
    from tao.config import Config


def build_pilot_experiments(config: "Config") -> Action:
    return Action(
        action_type="bash",
        bash_command="tao experiment-status .",
        description="Launch pilot experiments on RunPod",
        estimated_minutes=max(1, config.pilot_timeout // 60),
        experiment_monitor={
            "type": "pilot",
            "timeout_minutes": max(1, config.pilot_timeout // 60),
            "samples": config.pilot_samples,
            "seeds": config.pilot_seeds,
        },
    )


def build_experiment_cycle(config: "Config") -> Action:
    return Action(
        action_type="experiment_wait",
        description="Run full experiments on RunPod and monitor completion",
        estimated_minutes=max(1, config.experiment_timeout // 60),
        experiment_monitor={
            "type": "full",
            "timeout_minutes": max(1, config.experiment_timeout // 60),
            "seeds": config.full_seeds,
        },
    )
