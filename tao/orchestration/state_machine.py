"""Pipeline state machine — deterministic stage transitions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from tao.event_logger import read_events
from tao.orchestration.constants import PIPELINE_STAGES

if TYPE_CHECKING:
    from tao.config import Config
    from tao.workspace import Workspace


class StateMachine:
    """Deterministic state machine for the research pipeline.

    Computes next stage based on current stage + result,
    implementing all loop/pivot/quality-gate logic.
    """

    def __init__(self, workspace: "Workspace", config: "Config") -> None:
        self._ws = workspace
        self._cfg = config

    def natural_next_stage(
        self, current_stage: str, result: str = "", score: float = 0.0
    ) -> str:
        """Compute the next stage from current stage + result.

        Args:
            current_stage: Current pipeline stage name.
            result: Result text (may contain DECISION: PIVOT, REFINE, etc.).
            score: Numeric score (used by writing_final_review and quality_gate).

        Returns:
            Next stage name.
        """
        # --- Idea validation decision ---
        if current_stage == "idea_validation_decision":
            upper = result.upper()
            if "DECISION: PIVOT" in upper or "DECISION: REFINE" in upper:
                stage_visits = self._count_stage_visits("idea_validation_decision")
                within_stage_cap = stage_visits < self._cfg.idea_validation_rounds
                within_global_cap = (
                    self._count_review_loops() < self._cfg.max_review_rounds
                )
                if within_stage_cap and within_global_cap:
                    return "idea_debate"
            return self._next_in_pipeline(current_stage)

        # --- Experiment decision (pivot or proceed) ---
        if current_stage == "experiment_decision":
            upper = result.upper()
            if "DECISION: PIVOT" in upper:
                stage_visits = self._count_stage_visits("experiment_decision")
                within_stage_cap = stage_visits < self._cfg.idea_exp_cycles
                within_global_cap = (
                    self._count_review_loops() < self._cfg.max_review_rounds
                )
                if within_stage_cap and within_global_cap:
                    return "idea_debate"
            return self._next_in_pipeline(current_stage)

        # --- Writing final review (score gate) ---
        if current_stage == "writing_final_review":
            if score < 7.0:
                revisions = self._count_stage_visits("writing_final_review")
                if revisions < self._cfg.writing_revision_rounds:
                    return "writing_integrate"
            return self._next_in_pipeline(current_stage)

        # --- Quality gate ---
        if current_stage == "quality_gate":
            done, _, _, _, _ = self.is_pipeline_done(score)
            if done:
                return "done"
            return "literature_search"

        # --- Experiment stages: stay if tasks still running ---
        if current_stage in ("pilot_experiments", "experiment_cycle"):
            if "RUNNING" in result.upper():
                return current_stage  # stay in place

        # --- Default: next in pipeline ---
        return self._next_in_pipeline(current_stage)

    def is_pipeline_done(
        self, score: float = 0.0
    ) -> tuple[bool, float, float, int, int]:
        """Check if the pipeline should terminate.

        Returns:
            (done, score, threshold, max_iters, current_iteration)
        """
        status = self._ws.get_status()
        threshold = 7.0  # can be adjusted by reflection action_plan

        # Check for threshold adjustment from action plan
        action_plan = self._ws.read_json("reflection/action_plan.json")
        if action_plan and isinstance(action_plan, dict):
            threshold = action_plan.get("quality_threshold", threshold)

        max_iters = min(self._cfg.max_iterations, self._cfg.max_iterations_cap)
        current = status.iteration

        done = False
        if current >= max_iters:
            done = True
        elif score >= threshold and current >= 2:
            done = True

        return done, score, threshold, max_iters, current

    def clear_iteration_artifacts(self) -> None:
        """Clear ephemeral stage outputs for a new iteration."""
        self._ws.clear_iteration_artifacts()

    def reset_experiment_runtime_state(self) -> None:
        """Clear GPU progress and leases before starting experiment cycle."""
        for fname in ("exp/gpu_progress.json", "exp/experiment_state.json"):
            fp = self._ws.active_path(fname)
            if fp.exists():
                fp.unlink()

    def _next_in_pipeline(self, current_stage: str) -> str:
        """Get the next stage in the pipeline sequence."""
        try:
            idx = PIPELINE_STAGES.index(current_stage)
        except ValueError:
            return "done"
        if idx + 1 < len(PIPELINE_STAGES):
            return PIPELINE_STAGES[idx + 1]
        return "done"

    def _count_stage_visits(self, stage: str) -> int:
        """Count how many times a stage has been visited (from event log)."""
        events = read_events(self._ws.active_root / "logs", event_type="stage_complete")
        return sum(1 for e in events if e.get("stage") == stage)

    # Decision stages that can pivot back to idea_debate and burn review budget.
    _REVIEW_LOOP_STAGES = frozenset(
        {"idea_validation_decision", "experiment_decision"}
    )

    def _count_review_loops(self) -> int:
        """Total *pivot/refine* decisions across every decision stage.

        Only pivoting outcomes consume the global max_review_rounds budget.
        A normal PROCEED visit to idea_validation_decision or
        experiment_decision advances the pipeline without burning budget —
        counting those here would deny legitimate PIVOTs on the other
        decision stage (the regression caught in cc review 2026-04-16).
        """
        events = read_events(self._ws.active_root / "logs", event_type="stage_complete")
        count = 0
        for e in events:
            if e.get("stage") not in self._REVIEW_LOOP_STAGES:
                continue
            result = (e.get("result") or "").upper()
            if "PIVOT" in result or "REFINE" in result:
                count += 1
        return count
