"""Review and reflection action builders."""
from __future__ import annotations
from typing import TYPE_CHECKING
from tao.orchestration.models import Action

if TYPE_CHECKING:
    from tao.config import Config


def build_novelty_check(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-novelty-checker", "description": "Check idea novelty against literature"}],
        description="Novelty assessment",
        estimated_minutes=5,
    )


def build_simulated_review(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-simulated-reviewer", "description": "Simulate NeurIPS/ICML peer review"}],
        description="Simulated peer review",
        estimated_minutes=10,
    )
