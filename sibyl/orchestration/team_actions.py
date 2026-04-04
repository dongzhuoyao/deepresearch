"""Team action builders for multi-agent stages."""
from __future__ import annotations
from typing import TYPE_CHECKING
from sibyl.orchestration.models import Action

if TYPE_CHECKING:
    from sibyl.config import Config

IDEA_DEBATE_AGENTS = [
    {"name": "sibyl-innovator", "description": "Generate novel research ideas"},
    {"name": "sibyl-pragmatist", "description": "Evaluate practical feasibility"},
    {"name": "sibyl-theoretical", "description": "Assess theoretical soundness"},
    {"name": "sibyl-contrarian", "description": "Challenge assumptions and find weaknesses"},
    {"name": "sibyl-interdisciplinary", "description": "Cross-domain insights and analogies"},
    {"name": "sibyl-empiricist", "description": "Evidence-based evaluation"},
]

RESULT_DEBATE_AGENTS = [
    {"name": "sibyl-innovator", "description": "Interpret results creatively"},
    {"name": "sibyl-pragmatist", "description": "Practical implications of findings"},
    {"name": "sibyl-theoretical", "description": "Theoretical analysis of results"},
    {"name": "sibyl-contrarian", "description": "Challenge conclusions and find gaps"},
    {"name": "sibyl-interdisciplinary", "description": "Cross-domain comparison"},
    {"name": "sibyl-empiricist", "description": "Statistical rigor and reproducibility check"},
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
                {"skill": "sibyl-synthesizer", "description": "Synthesize best idea from debate"},
            ],
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
                {"skill": "sibyl-result-synthesizer", "description": "Synthesize result analysis"},
            ],
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
                {"name": "sibyl-section-critic", "description": "Critique each section for quality"},
                {"name": "sibyl-editor", "description": "Integrate sections and ensure coherence"},
            ],
        },
        description="Cross-critique and integrate paper sections",
        estimated_minutes=15,
    )


def build_review(config: "Config") -> Action:
    agents = [
        {"name": "sibyl-supervisor", "description": "Supervisor structural review"},
        {"name": "sibyl-critic", "description": "Critical content review"},
    ]
    return Action(
        action_type="team",
        team={
            "name": "review_team",
            "prompt": "Final structural and content review of the paper",
            "agents": agents,
        },
        description="Final paper review by supervisor and critic",
        estimated_minutes=10,
    )
