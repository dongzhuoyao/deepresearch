"""Writing action builders."""
from __future__ import annotations
from typing import TYPE_CHECKING
from tao.orchestration.models import Action
from tao.orchestration.constants import PAPER_SECTIONS

if TYPE_CHECKING:
    from tao.config import Config


def build_writing_sections(config: "Config") -> Action:
    if config.writing_mode == "parallel":
        agents = [
            {
                "name": "tao-section-writer",
                "description": f"Write {title} section",
                "args": {"section": sid},
            }
            for sid, title in PAPER_SECTIONS
        ]
        return Action(
            action_type="skills_parallel",
            agents=agents,
            description="Write all paper sections in parallel",
            estimated_minutes=20,
        )
    return Action(
        action_type="skill",
        skills=[{"name": "tao-sequential-writer", "description": "Write all sections sequentially"}],
        description="Write paper sections sequentially",
        estimated_minutes=30,
    )
