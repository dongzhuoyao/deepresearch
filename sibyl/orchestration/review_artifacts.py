"""Review and reflection action builders."""
from __future__ import annotations
from typing import TYPE_CHECKING
from sibyl.orchestration.models import Action

if TYPE_CHECKING:
    from sibyl.config import Config


def build_novelty_check(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "sibyl-novelty-checker", "description": "Check idea novelty against literature"}],
        description="Novelty assessment",
        estimated_minutes=5,
    )


def build_simulated_review(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "sibyl-simulated-reviewer", "description": "Simulate NeurIPS/ICML peer review"}],
        description="Simulated peer review",
        estimated_minutes=10,
    )
