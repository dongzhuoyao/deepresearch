"""Pipeline lifecycle — generates actions for each stage."""
from __future__ import annotations
from typing import TYPE_CHECKING

from tao.orchestration.models import Action
from tao.orchestration.state_machine import StateMachine
from tao.orchestration.simple_actions import (
    build_literature_search,
    build_planning,
    build_idea_validation,
    build_experiment_decision,
    build_writing_outline,
    build_writing_final_review,
    build_writing_latex,
    build_writing_teaser,
    build_reflection,
    build_quality_gate,
)
from tao.orchestration.team_actions import (
    build_idea_debate,
    build_result_debate,
    build_writing_integrate,
    build_review,
)
from tao.orchestration.experiment_actions import (
    build_experiment_cycle,
    build_pilot_experiments,
)
from tao.orchestration.writing_artifacts import (
    build_writing_assets,
    build_writing_sections,
)
from tao.event_logger import log_event

if TYPE_CHECKING:
    from tao.config import Config
    from tao.workspace import Workspace


class Lifecycle:
    """Generates Action objects for pipeline stages and records results."""

    def __init__(self, workspace: "Workspace", config: "Config") -> None:
        self._ws = workspace
        self._cfg = config
        self._sm = StateMachine(workspace, config)

    def get_next_action(self) -> Action:
        """Generate the next action based on current workspace state."""
        status = self._ws.get_status()
        stage = status.stage
        iteration = status.iteration

        # Map stages to action builders
        builders = {
            "init": self._action_init,
            "literature_search": lambda: build_literature_search(self._cfg),
            "idea_debate": lambda: build_idea_debate(self._cfg),
            "planning": lambda: build_planning(self._cfg),
            "pilot_experiments": lambda: build_pilot_experiments(self._cfg),
            "idea_validation_decision": lambda: build_idea_validation(self._cfg),
            "experiment_cycle": lambda: build_experiment_cycle(self._cfg),
            "result_debate": lambda: build_result_debate(self._cfg),
            "experiment_decision": lambda: build_experiment_decision(self._cfg),
            "writing_outline": lambda: build_writing_outline(self._cfg),
            "writing_assets": lambda: build_writing_assets(self._cfg),
            "writing_sections": lambda: build_writing_sections(self._cfg),
            "writing_integrate": lambda: build_writing_integrate(self._cfg),
            "writing_teaser": lambda: build_writing_teaser(self._cfg),
            "writing_final_review": lambda: build_writing_final_review(self._cfg),
            "writing_latex": lambda: build_writing_latex(self._cfg),
            "review": lambda: build_review(self._cfg),
            "reflection": lambda: build_reflection(self._cfg),
            "quality_gate": lambda: build_quality_gate(self._cfg),
            "done": self._action_done,
        }

        builder = builders.get(stage, self._action_done)
        action = builder()
        action.stage = stage
        action.iteration = iteration
        return action

    def record_result(self, stage: str, result: str, score: float = 0.0) -> str:
        """Record stage result and advance to next stage.

        Returns the next stage name.
        """
        # Log the completion event
        log_event(
            self._ws.active_root / "logs",
            "stage_complete",
            {"stage": stage, "result": result[:200], "score": score},
        )

        # Compute next stage
        next_stage = self._sm.natural_next_stage(stage, result, score)

        # Freeze research contract on planning -> pilot_experiments transition.
        # Missing contracts are tolerated (tests may bypass the planning stage);
        # we log and continue instead of crashing the lifecycle.
        if stage == "planning" and next_stage == "pilot_experiments":
            try:
                from tao.orchestration.contract import freeze_contract, load_contract
                load_contract(self._ws)  # raises if missing — skip freeze silently
                freeze_contract(self._ws)
            except Exception as e:
                log_event(
                    self._ws.active_root / "logs",
                    "contract_freeze_skipped",
                    {"error": str(e)},
                )

        # Handle iteration advancement
        if next_stage == "literature_search" and stage == "quality_gate":
            # Starting new iteration
            self._ws.new_iteration()
            self._ws.update_stage("literature_search")
        elif next_stage == "done":
            self._ws.update_stage("done")
        else:
            self._ws.update_stage(next_stage)

        return next_stage

    # --- Action builders (only for stages without a standalone builder) ---

    def _action_init(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-literature", "description": "Initialize research workspace"}],
            description="Initialize project and prepare for literature search",
            estimated_minutes=2,
        )

    def _action_done(self) -> Action:
        return Action(
            action_type="done",
            description="Pipeline complete",
            estimated_minutes=0,
        )
