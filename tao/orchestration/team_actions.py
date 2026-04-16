"""Team action builders for multi-agent stages."""
from __future__ import annotations
from typing import TYPE_CHECKING
from tao.orchestration.models import Action

if TYPE_CHECKING:
    from tao.config import Config

IDEA_DEBATE_AGENTS = [
    {"name": "tao-innovator", "description": "Generate novel research ideas"},
    {"name": "tao-pragmatist", "description": "Evaluate practical feasibility"},
    {"name": "tao-theoretical", "description": "Assess theoretical soundness"},
    {"name": "tao-contrarian", "description": "Challenge assumptions and find weaknesses"},
    {"name": "tao-interdisciplinary", "description": "Cross-domain insights and analogies"},
    {"name": "tao-empiricist", "description": "Evidence-based evaluation"},
]

RESULT_DEBATE_AGENTS = [
    {"name": "tao-innovator", "description": "Interpret results creatively"},
    {"name": "tao-pragmatist", "description": "Practical implications of findings"},
    {"name": "tao-theoretical", "description": "Theoretical analysis of results"},
    {"name": "tao-contrarian", "description": "Challenge conclusions and find gaps"},
    {"name": "tao-interdisciplinary", "description": "Cross-domain comparison"},
    {"name": "tao-empiricist", "description": "Statistical rigor and reproducibility check"},
]


def build_idea_debate(config: "Config") -> Action:
    return Action(
        action_type="team",
        team={
            "name": "idea_debate_team",
            "prompt": "Debate and refine research ideas through multi-perspective analysis",
            "agents": IDEA_DEBATE_AGENTS,
            "rounds": config.debate_rounds,
            "post_steps": [
                {"skill": "tao-synthesizer", "description": "Synthesize best idea from debate"},
            ],
            "context_isolation": True,
            "isolation_inputs": ["baseline_paper", "candidate"],
        },
        description="Multi-agent idea debate and synthesis",
        estimated_minutes=15,
    )


def build_result_debate(config: "Config") -> Action:
    return Action(
        action_type="team",
        team={
            "name": "result_debate_team",
            "prompt": "Analyze and debate experiment results from multiple perspectives",
            "agents": RESULT_DEBATE_AGENTS,
            "rounds": config.debate_rounds,
            "post_steps": [
                {"skill": "tao-result-synthesizer", "description": "Synthesize result analysis"},
            ],
            "context_isolation": True,
            "isolation_inputs": ["contract", "experiment_record"],
        },
        description="Multi-agent result analysis and debate",
        estimated_minutes=15,
    )


def build_writing_integrate(config: "Config") -> Action:
    return Action(
        action_type="team",
        team={
            "name": "writing_review_team",
            "prompt": "Cross-critique paper sections, then integrate and edit",
            "agents": [
                {"name": "tao-section-critic", "description": "Critique each section for quality"},
                {"name": "tao-editor", "description": "Integrate sections and ensure coherence"},
            ],
        },
        description="Cross-critique and integrate paper sections",
        estimated_minutes=15,
    )


def build_review(config: "Config") -> Action:
    agents = [
        {"name": "tao-supervisor", "description": "Supervisor structural review"},
        {"name": "tao-critic", "description": "Critical content review"},
        {
            "name": "tao-codex-reviewer",
            "description": (
                "Codex/GPT-5 independent review (isolated context: contract + "
                "one section at a time, no sibling reviewer outputs)"
            ),
        },
    ]
    return Action(
        action_type="team",
        team={
            "name": "review_team",
            "prompt": "Final structural and content review of the paper",
            "agents": agents,
            "context_isolation": True,
            "isolation_inputs": ["contract", "section"],
        },
        description="Final paper review: supervisor + critic + Codex",
        estimated_minutes=10,
    )
