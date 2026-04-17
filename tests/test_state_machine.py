"""Tests for pipeline state machine."""
import json

from tao.orchestration.state_machine import StateMachine
from tao.workspace import Workspace
from tao.config import Config


def _make_sm(tmp_path, **config_overrides) -> StateMachine:
    """Create a StateMachine with workspace and config."""
    cfg = Config()
    for k, v in config_overrides.items():
        setattr(cfg, k, v)
    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("test topic")
    return StateMachine(ws, cfg)


class TestForwardTransitions:
    def test_init_to_literature(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("init") == "literature_search"

    def test_literature_to_idea_debate(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("literature_search") == "idea_debate"

    def test_idea_debate_to_planning(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("idea_debate") == "planning"

    def test_planning_to_pilot(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("planning") == "pilot_experiments"

    def test_writing_latex_to_review(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("writing_latex") == "review"

    def test_review_to_reflection(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("review") == "reflection"

    def test_reflection_to_quality_gate(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("reflection") == "quality_gate"


class TestPivotLogic:
    def test_experiment_decision_pivot(self, tmp_path):
        sm = _make_sm(tmp_path, idea_exp_cycles=3)
        # No prior visits = should pivot back
        next_stage = sm.natural_next_stage(
            "experiment_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "idea_debate"

    def test_experiment_decision_pivot_exhausted(self, tmp_path):
        sm = _make_sm(tmp_path, idea_exp_cycles=1)
        # Simulate 1 prior visit
        ws = sm._ws
        from tao.event_logger import log_event

        log_event(
            ws.active_root / "logs",
            "stage_complete",
            {"stage": "experiment_decision"},
        )
        next_stage = sm.natural_next_stage(
            "experiment_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "writing_outline"

    def test_experiment_decision_proceed(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "experiment_decision", result="DECISION: PROCEED"
        )
        assert next_stage == "writing_outline"


class TestValidationLogic:
    def test_validation_refine(self, tmp_path):
        sm = _make_sm(tmp_path, idea_validation_rounds=3)
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="DECISION: REFINE"
        )
        assert next_stage == "idea_debate"

    def test_validation_pivot(self, tmp_path):
        sm = _make_sm(tmp_path, idea_validation_rounds=3)
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "idea_debate"

    def test_validation_advance(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="ADVANCE"
        )
        assert next_stage == "experiment_cycle"

    def test_validation_exhausted(self, tmp_path):
        sm = _make_sm(tmp_path, idea_validation_rounds=1)
        ws = sm._ws
        from tao.event_logger import log_event

        log_event(
            ws.active_root / "logs",
            "stage_complete",
            {"stage": "idea_validation_decision"},
        )
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="DECISION: REFINE"
        )
        assert next_stage == "experiment_cycle"


class TestWritingRevision:
    def test_low_score_revision(self, tmp_path):
        sm = _make_sm(tmp_path, writing_revision_rounds=2)
        next_stage = sm.natural_next_stage("writing_final_review", score=5.5)
        assert next_stage == "writing_integrate"

    def test_high_score_proceed(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage("writing_final_review", score=8.0)
        assert next_stage == "writing_latex"

    def test_low_score_exhausted(self, tmp_path):
        sm = _make_sm(tmp_path, writing_revision_rounds=1)
        ws = sm._ws
        from tao.event_logger import log_event

        log_event(
            ws.active_root / "logs",
            "stage_complete",
            {"stage": "writing_final_review"},
        )
        next_stage = sm.natural_next_stage("writing_final_review", score=5.0)
        assert next_stage == "writing_latex"


class TestNewWritingStages:
    def test_writing_outline_to_assets(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("writing_outline") == "writing_assets"

    def test_writing_assets_to_sections(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("writing_assets") == "writing_sections"

    def test_writing_teaser_to_final_review(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("writing_teaser") == "writing_final_review"


class TestQualityGate:
    def test_quality_gate_done_high_score(self, tmp_path):
        sm = _make_sm(tmp_path, max_iterations=10)
        sm._ws.update_stage_and_iteration("quality_gate", 3)
        next_stage = sm.natural_next_stage("quality_gate", score=8.0)
        assert next_stage == "done"

    def test_quality_gate_loop_low_score(self, tmp_path):
        sm = _make_sm(tmp_path, max_iterations=10)
        sm._ws.update_stage_and_iteration("quality_gate", 1)
        next_stage = sm.natural_next_stage("quality_gate", score=5.0)
        assert next_stage == "literature_search"

    def test_quality_gate_done_max_iters(self, tmp_path):
        sm = _make_sm(tmp_path, max_iterations=3)
        sm._ws.update_stage_and_iteration("quality_gate", 3)
        next_stage = sm.natural_next_stage("quality_gate", score=4.0)
        assert next_stage == "done"

    def test_quality_gate_not_done_iteration_1(self, tmp_path):
        """Even with high score, iteration 1 is too early to finish."""
        sm = _make_sm(tmp_path, max_iterations=10)
        sm._ws.update_stage_and_iteration("quality_gate", 1)
        next_stage = sm.natural_next_stage("quality_gate", score=9.0)
        assert next_stage == "literature_search"

    def test_is_pipeline_done(self, tmp_path):
        sm = _make_sm(tmp_path, max_iterations=5)
        sm._ws.update_stage_and_iteration("quality_gate", 3)
        done, score, threshold, max_iters, current = sm.is_pipeline_done(8.5)
        assert done is True
        assert current == 3

    def test_is_pipeline_done_with_custom_threshold(self, tmp_path):
        sm = _make_sm(tmp_path, max_iterations=10)
        sm._ws.update_stage_and_iteration("quality_gate", 3)
        # Write action plan with custom threshold
        sm._ws.write_json(
            "reflection/action_plan.json", {"quality_threshold": 9.0}
        )
        done, score, threshold, max_iters, current = sm.is_pipeline_done(8.0)
        assert done is False
        assert threshold == 9.0


class TestExperimentPolling:
    def test_pilot_stays_when_running(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "pilot_experiments", result="RUNNING: 2/5 tasks"
        )
        assert next_stage == "pilot_experiments"

    def test_pilot_advances_when_done(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "pilot_experiments", result="ALL COMPLETE"
        )
        assert next_stage == "idea_validation_decision"

    def test_experiment_cycle_stays_when_running(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "experiment_cycle", result="RUNNING: 1/3 tasks"
        )
        assert next_stage == "experiment_cycle"

    def test_experiment_cycle_advances_when_done(self, tmp_path):
        sm = _make_sm(tmp_path)
        next_stage = sm.natural_next_stage(
            "experiment_cycle", result="ALL TASKS DONE"
        )
        assert next_stage == "result_debate"


class TestEdgeCases:
    def test_unknown_stage_returns_done(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("nonexistent_stage") == "done"

    def test_done_stage_returns_done(self, tmp_path):
        sm = _make_sm(tmp_path)
        assert sm.natural_next_stage("done") == "done"

    def test_empty_result_string(self, tmp_path):
        sm = _make_sm(tmp_path)
        # experiment_decision with empty result should proceed normally
        next_stage = sm.natural_next_stage("experiment_decision", result="")
        assert next_stage == "writing_outline"

    def test_reset_experiment_runtime_state(self, tmp_path):
        sm = _make_sm(tmp_path)
        # Create the files
        gpu_progress = sm._ws.active_path("exp/gpu_progress.json")
        gpu_progress.parent.mkdir(parents=True, exist_ok=True)
        gpu_progress.write_text("{}", encoding="utf-8")
        exp_state = sm._ws.active_path("exp/experiment_state.json")
        exp_state.write_text("{}", encoding="utf-8")

        sm.reset_experiment_runtime_state()
        assert not gpu_progress.exists()
        assert not exp_state.exists()

    def test_clear_iteration_artifacts(self, tmp_path):
        sm = _make_sm(tmp_path)
        # Create an artifact
        sm._ws.write_file("idea/test.txt", "hello")
        assert sm._ws.active_path("idea/test.txt").exists()

        sm.clear_iteration_artifacts()
        # The file should be gone, but the directory structure recreated
        assert not sm._ws.active_path("idea/test.txt").exists()
        assert sm._ws.active_path("idea").is_dir()


class TestMaxReviewRoundsCap:
    def test_idea_validation_respects_global_cap(self, tmp_path):
        sm = _make_sm(tmp_path, idea_validation_rounds=10, max_review_rounds=2)
        from tao.event_logger import log_event
        ws = sm._ws
        for _ in range(2):
            log_event(
                ws.active_root / "logs", "stage_complete",
                {"stage": "idea_validation_decision"},
            )
        # Two prior revisits = global cap reached; must force forward even on PIVOT.
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "experiment_cycle"

    def test_experiment_decision_respects_global_cap(self, tmp_path):
        sm = _make_sm(tmp_path, idea_exp_cycles=10, max_review_rounds=1)
        from tao.event_logger import log_event
        ws = sm._ws
        log_event(
            ws.active_root / "logs", "stage_complete",
            {"stage": "experiment_decision"},
        )
        # One prior visit = global cap (1) reached; PIVOT must be denied.
        next_stage = sm.natural_next_stage(
            "experiment_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "writing_outline"

    def test_idea_validation_allows_refine_within_both_caps(self, tmp_path):
        sm = _make_sm(tmp_path, idea_validation_rounds=5, max_review_rounds=5)
        next_stage = sm.natural_next_stage(
            "idea_validation_decision", result="DECISION: REFINE"
        )
        assert next_stage == "idea_debate"

    def test_global_cap_is_shared_across_decision_stages(self, tmp_path):
        """max_review_rounds must bound TOTAL review loops across both
        decision stages, not just the current stage. Previously a
        max_review_rounds=1 setting allowed 1 pivot in idea_validation
        AND 1 pivot in experiment_decision = 2 loops total. Codex review
        2026-04-16 flagged this.
        """
        sm = _make_sm(
            tmp_path,
            idea_validation_rounds=10,
            idea_exp_cycles=10,
            max_review_rounds=1,
        )
        from tao.event_logger import log_event
        ws = sm._ws
        # Simulate one prior pivot via idea_validation_decision.
        log_event(
            ws.active_root / "logs", "stage_complete",
            {"stage": "idea_validation_decision"},
        )
        # experiment_decision has zero prior visits of its own, but the
        # GLOBAL review-loop budget is already spent. PIVOT must be denied.
        next_stage = sm.natural_next_stage(
            "experiment_decision", result="DECISION: PIVOT"
        )
        assert next_stage == "writing_outline"
