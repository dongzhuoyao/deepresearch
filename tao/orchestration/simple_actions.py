"""Simple action builders for single-skill and bash stages."""
from __future__ import annotations
from typing import TYPE_CHECKING
from tao.orchestration.models import Action

if TYPE_CHECKING:
    from tao.config import Config


def build_literature_search(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-literature", "description": "Search literature on arXiv and web"}],
        description="Conduct literature survey",
        estimated_minutes=10,
    )


def build_planning(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{
            "name": "tao-planner",
            "description": (
                "Design experiment plan with task dependencies AND write research "
                "contract (hypothesis, success/failure signals, ablations) to "
                "plan/contract.json"
            ),
        }],
        description="Create experiment methodology, task plan, and research contract",
        estimated_minutes=10,
    )


def build_idea_validation(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-idea-validation-decision", "description": "Evaluate pilots: ADVANCE, REFINE, or PIVOT"}],
        description="Validate idea based on pilot experiment results",
        estimated_minutes=5,
    )


def build_experiment_decision(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-supervisor-decision", "description": "Decide PROCEED or PIVOT based on full results"}],
        description="Supervisor decision on experiment direction",
        estimated_minutes=5,
    )


def build_writing_outline(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-outline-writer", "description": "Create paper outline"}],
        description="Write paper outline",
        estimated_minutes=5,
    )


def build_writing_final_review(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-final-critic", "description": "Score paper 0-10, identify weaknesses"}],
        description="Final paper quality review and scoring",
        estimated_minutes=5,
    )


def build_writing_latex(config: "Config") -> Action:
    return Action(
        action_type="bash",
        bash_command="tao latex-compile .",
        description="Convert to LaTeX and compile PDF",
        estimated_minutes=5,
    )


def build_reflection(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-reflection", "description": "Extract lessons, classify issues, create action plan"}],
        description="Reflect on iteration and extract lessons",
        estimated_minutes=5,
    )


def build_quality_gate(config: "Config") -> Action:
    return Action(
        action_type="done",
        description="Quality gate — deterministic DONE/iterate decision",
        estimated_minutes=1,
    )


def build_writing_teaser(config: "Config") -> Action:
    return Action(
        action_type="skill",
        skills=[{"name": "tao-teaser-generator", "description": "Create Figure 1 (teaser) combining method + key result"}],
        description="Generate teaser figure (Figure 1)",
        estimated_minutes=10,
    )
