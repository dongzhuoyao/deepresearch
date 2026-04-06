"""Rebuttal action builders."""
from __future__ import annotations
from tao.orchestration.models import Action


def build_parse_reviews() -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-rebuttal-strategist", "description": "Parse and categorize reviewer comments"}],
        description="Parse reviewer comments",
        estimated_minutes=5,
    )


def build_strategy() -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-rebuttal-strategist", "description": "Develop rebuttal strategy"}],
        description="Develop rebuttal strategy",
        estimated_minutes=5,
    )


def build_rebuttal_draft() -> Action:
    return Action(
        action_type="team",
        team={
            "name": "rebuttal_team",
            "prompt": "Draft point-by-point rebuttal",
            "agents": [
                {"name": "tao-rebuttal-writer", "description": "Write rebuttal text"},
                {"name": "tao-rebuttal-checker", "description": "Verify evidence and accuracy"},
            ],
        },
        description="Draft rebuttal with evidence checking",
        estimated_minutes=15,
    )


def build_simulated_review() -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-simulated-reviewer", "description": "Simulate reviewer response to rebuttal"}],
        description="Simulated peer review of rebuttal",
        estimated_minutes=5,
    )


def build_final_synthesis() -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-rebuttal-synthesizer", "description": "Produce final polished rebuttal"}],
        description="Synthesize final rebuttal",
        estimated_minutes=10,
    )
