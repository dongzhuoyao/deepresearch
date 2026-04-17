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
        skills=[{
            "name": "tao-sequential-writer",
            "description": (
                "Write all sections sequentially; after each, verify empirical claims "
                "cite [signal:*] from plan/contract.json (tao.orchestration.writing_gate)"
            ),
        }],
        description="Write paper sections sequentially",
        estimated_minutes=30,
    )


def build_writing_assets(config: "Config") -> Action:
    # Always sequential: tables must complete before figures because
    # exp_figure_generator reads writing/tables/table_summary.json.
    # All writing_mode values (parallel, sequential, codex) use this path —
    # codex mode only affects text writing, not asset generation.
    return Action(
        action_type="skill",
        skills=[{"name": "tao-asset-generator", "description": "Generate tables, experimental figures, and method diagram"}],
        description="Generate visual assets: tables → exp figures → method figure",
        estimated_minutes=20,
    )
