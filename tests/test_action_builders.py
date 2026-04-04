"""Tests for action builders."""
from sibyl.config import Config
from sibyl.orchestration.simple_actions import (
    build_literature_search, build_planning, build_idea_validation,
    build_experiment_decision, build_writing_outline, build_writing_final_review,
    build_writing_latex, build_reflection, build_quality_gate,
)
from sibyl.orchestration.team_actions import (
    build_idea_debate, build_result_debate, build_writing_integrate, build_review,
)
from sibyl.orchestration.experiment_actions import (
    build_pilot_experiments, build_experiment_cycle,
)
from sibyl.orchestration.writing_artifacts import build_writing_sections
from sibyl.orchestration.review_artifacts import build_novelty_check, build_simulated_review


class TestSimpleActions:
    def test_literature_search(self):
        action = build_literature_search(Config())
        assert action.action_type == "skill"
        assert "literature" in action.skills[0]["name"].lower()

    def test_planning(self):
        action = build_planning(Config())
        assert action.action_type == "skill"

    def test_idea_validation(self):
        action = build_idea_validation(Config())
        assert action.action_type == "skill"

    def test_experiment_decision(self):
        action = build_experiment_decision(Config())
        assert action.action_type == "skill"

    def test_writing_outline(self):
        action = build_writing_outline(Config())
        assert action.action_type == "skill"

    def test_writing_final_review(self):
        action = build_writing_final_review(Config())
        assert action.action_type == "skill"

    def test_writing_latex(self):
        action = build_writing_latex(Config())
        assert action.action_type == "bash"
        assert "latex" in action.bash_command.lower()

    def test_reflection(self):
        action = build_reflection(Config())
        assert action.action_type == "skill"

    def test_quality_gate(self):
        action = build_quality_gate(Config())
        assert action.action_type == "done"


class TestTeamActions:
    def test_idea_debate(self):
        action = build_idea_debate(Config())
        assert action.action_type == "team"
        assert len(action.team["agents"]) == 6
        assert action.team["post_steps"][0]["skill"] == "sibyl-synthesizer"

    def test_result_debate(self):
        action = build_result_debate(Config())
        assert action.action_type == "team"
        assert len(action.team["agents"]) == 6

    def test_writing_integrate(self):
        action = build_writing_integrate(Config())
        assert action.action_type == "team"
        assert len(action.team["agents"]) == 2

    def test_review(self):
        action = build_review(Config())
        assert action.action_type == "team"
        assert len(action.team["agents"]) == 2


class TestExperimentActions:
    def test_pilot(self):
        action = build_pilot_experiments(Config())
        assert action.action_type == "bash"
        assert action.experiment_monitor["type"] == "pilot"

    def test_experiment_cycle(self):
        action = build_experiment_cycle(Config())
        assert action.action_type == "experiment_wait"
        assert action.experiment_monitor["type"] == "full"


class TestWritingActions:
    def test_parallel_sections(self):
        cfg = Config()
        cfg.writing_mode = "parallel"
        action = build_writing_sections(cfg)
        assert action.action_type == "skills_parallel"
        assert len(action.agents) == 6  # 6 paper sections

    def test_sequential_sections(self):
        cfg = Config()
        cfg.writing_mode = "sequential"
        action = build_writing_sections(cfg)
        assert action.action_type == "skill"


class TestReviewArtifacts:
    def test_novelty_check(self):
        action = build_novelty_check(Config())
        assert action.action_type == "skill"

    def test_simulated_review(self):
        action = build_simulated_review(Config())
        assert action.action_type == "skill"
