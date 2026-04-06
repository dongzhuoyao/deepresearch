"""Tests for rebuttal pipeline."""
import json
from tao.rebuttal.constants import REBUTTAL_STAGES
from tao.rebuttal.config import RebuttalConfig
from tao.rebuttal.state_machine import RebuttalStateMachine
from tao.rebuttal.scoring import compute_rebuttal_score, track_score_trajectory
from tao.rebuttal.workspace_setup import setup_rebuttal_workspace
from tao.rebuttal.prompt_helpers import format_review_context, format_rebuttal_prompt
from tao.rebuttal.actions import (
    build_parse_reviews, build_strategy, build_rebuttal_draft,
    build_simulated_review, build_final_synthesis,
)
from tao.rebuttal.orchestrator import RebuttalOrchestrator
from tao.rebuttal.cli import cli_rebuttal_init, cli_rebuttal_status


class TestRebuttalStateMachine:
    def test_forward_progression(self):
        sm = RebuttalStateMachine()
        assert sm.next_stage("parse_reviews") == "strategy"
        assert sm.next_stage("strategy") == "rebuttal_draft"
        assert sm.next_stage("rebuttal_draft") == "simulated_review"

    def test_score_threshold_met(self):
        sm = RebuttalStateMachine(score_threshold=7.0)
        assert sm.next_stage("score_evaluate", score=8.0) == "final_synthesis"

    def test_score_below_threshold(self):
        sm = RebuttalStateMachine(score_threshold=7.0, max_rounds=3)
        assert sm.next_stage("score_evaluate", score=5.0, round_num=1) == "rebuttal_draft"

    def test_max_rounds_reached(self):
        sm = RebuttalStateMachine(max_rounds=2)
        assert sm.next_stage("score_evaluate", score=3.0, round_num=2) == "final_synthesis"

    def test_is_done(self):
        sm = RebuttalStateMachine()
        assert sm.is_done("done") is True
        assert sm.is_done("strategy") is False


class TestScoring:
    def test_empty_rebuttal(self):
        assert compute_rebuttal_score({}, "") == 0.0

    def test_basic_rebuttal(self):
        score = compute_rebuttal_score({}, "This is a short rebuttal")
        assert 4.0 <= score <= 7.0

    def test_evidence_rich(self):
        text = "Our table 1 shows the data from experiment results with significant p-value improvements in figure 2"
        score = compute_rebuttal_score({}, text)
        assert score > 6.0

    def test_trajectory(self):
        assert track_score_trajectory([5.0, 7.0]) == "improving"
        assert track_score_trajectory([7.0, 5.0]) == "declining"
        assert track_score_trajectory([7.0]) == "insufficient"


class TestWorkspaceSetup:
    def test_setup(self, tmp_path):
        rebuttal_dir = setup_rebuttal_workspace(tmp_path)
        assert (rebuttal_dir / "reviews").is_dir()
        assert (rebuttal_dir / "drafts").is_dir()
        assert (rebuttal_dir / "final").is_dir()


class TestPromptHelpers:
    def test_format_reviews(self):
        reviews = [
            {"reviewer": "R1", "score": 6, "comments": "Needs more baselines"},
            {"reviewer": "R2", "score": 7, "comments": "Good idea, weak eval"},
        ]
        ctx = format_review_context(reviews)
        assert "R1" in ctx
        assert "baselines" in ctx

    def test_format_rebuttal_prompt(self):
        prompt = format_rebuttal_prompt(
            "review context",
            strategy="address baselines",
            prior_draft="draft v1",
        )
        assert "review context" in prompt
        assert "address baselines" in prompt


class TestActions:
    def test_parse_reviews(self):
        a = build_parse_reviews()
        assert a.action_type == "skill"

    def test_rebuttal_draft(self):
        a = build_rebuttal_draft()
        assert a.action_type == "team"
        assert len(a.team["agents"]) == 2

    def test_final_synthesis(self):
        a = build_final_synthesis()
        assert a.action_type == "skill"


class TestOrchestrator:
    def test_init_and_progress(self, tmp_path):
        reviews = [{"reviewer": "R1", "score": 5, "comments": "Weak baselines"}]
        orch = RebuttalOrchestrator(tmp_path)
        stage = orch.init(reviews)
        assert stage == "parse_reviews"
        assert not orch.is_done()

    def test_record_and_advance(self, tmp_path):
        orch = RebuttalOrchestrator(tmp_path)
        orch.init([{"reviewer": "R1", "score": 5, "comments": "test"}])

        next_s = orch.record_result("parse_reviews")
        assert next_s == "strategy"

        next_s = orch.record_result("strategy")
        assert next_s == "rebuttal_draft"

    def test_full_pipeline(self, tmp_path):
        orch = RebuttalOrchestrator(tmp_path, RebuttalConfig(max_rounds=1, score_threshold=7.0))
        orch.init([{"reviewer": "R1", "score": 5, "comments": "test"}])

        orch.record_result("parse_reviews")
        orch.record_result("strategy")
        orch.record_result("rebuttal_draft")
        orch.record_result("simulated_review")
        next_s = orch.record_result("score_evaluate", score=8.0)
        assert next_s == "final_synthesis"
        next_s = orch.record_result("final_synthesis")
        assert next_s == "done"
        assert orch.is_done()

    def test_status(self, tmp_path):
        orch = RebuttalOrchestrator(tmp_path)
        orch.init([{"reviewer": "R1", "score": 5, "comments": "test"}])
        status = orch.get_status()
        assert status["stage"] == "parse_reviews"
        assert status["round"] == 0


class TestCli:
    def test_init_and_status(self, tmp_path):
        reviews_file = tmp_path / "reviews.json"
        reviews_file.write_text(json.dumps([{"reviewer": "R1", "score": 5, "comments": "test"}]))

        result = cli_rebuttal_init(str(tmp_path), str(reviews_file))
        data = json.loads(result)
        assert data["stage"] == "parse_reviews"

        status = cli_rebuttal_status(str(tmp_path))
        data = json.loads(status)
        assert data["stage"] == "parse_reviews"
