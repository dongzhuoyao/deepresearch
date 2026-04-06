"""Tests for reflection and evolution."""
import time
from tao.reflection import (
    log_iteration, load_iteration_log, get_quality_trajectory, assess_trajectory,
)
from tao.evolution import (
    IssueCategory, normalize_issue_entry, compute_effectiveness,
    generate_agent_overlay, log_evolution_event, load_evolution_log,
)
from tao.orchestration.reflection_postprocess import run_post_reflection_hook


class TestReflection:
    def test_log_and_load(self, tmp_path):
        log_iteration(tmp_path, 1, "reflection", "improved writing", 3, 2, 7.5)
        log_iteration(tmp_path, 2, "reflection", "better experiments", 1, 1, 8.2)
        entries = load_iteration_log(tmp_path)
        assert len(entries) == 2
        assert entries[0]["quality_score"] == 7.5

    def test_quality_trajectory(self, tmp_path):
        log_iteration(tmp_path, 1, "reflection", "", 0, 0, 6.0)
        log_iteration(tmp_path, 2, "reflection", "", 0, 0, 7.0)
        log_iteration(tmp_path, 3, "reflection", "", 0, 0, 8.0)
        scores = get_quality_trajectory(tmp_path)
        assert scores == [6.0, 7.0, 8.0]

    def test_assess_improving(self):
        assert assess_trajectory([5.0, 6.0, 7.0]) == "improving"

    def test_assess_declining(self):
        assert assess_trajectory([8.0, 7.0, 6.0]) == "declining"

    def test_assess_stagnant(self):
        assert assess_trajectory([7.0, 6.0, 7.0]) == "stagnant"

    def test_assess_insufficient(self):
        assert assess_trajectory([7.0]) == "insufficient_data"


class TestEvolution:
    def test_normalize_issue(self):
        raw = {"description": "GPU OOM on A100", "category": "system", "severity": "high"}
        norm = normalize_issue_entry(raw)
        assert norm["category"] == "system"
        assert "issue_key" in norm

    def test_normalize_synonym(self):
        raw = {"description": "baseline missing", "message": "No baseline comparison"}
        norm = normalize_issue_entry(raw)
        assert norm["category"] == "experiment"

    def test_compute_effectiveness_all_success(self):
        now = time.time()
        history = [{"ts": now, "success": True}, {"ts": now - 100, "success": True}]
        eff = compute_effectiveness(history)
        assert eff > 0.9

    def test_compute_effectiveness_all_failure(self):
        now = time.time()
        history = [{"ts": now, "success": False}]
        eff = compute_effectiveness(history)
        assert eff == 0.0

    def test_compute_effectiveness_empty(self):
        assert compute_effectiveness([]) == 0.0

    def test_generate_overlay(self):
        lessons = [
            {"description": "Missing baselines", "category": "experiment", "suggestion": "Add baselines", "ts": time.time()},
            {"description": "Weak analysis", "category": "analysis", "suggestion": "Add p-values", "ts": time.time()},
        ]
        overlay = generate_agent_overlay("experimenter", lessons)
        assert "Missing baselines" in overlay
        assert "Add baselines" in overlay

    def test_generate_overlay_irrelevant(self):
        lessons = [
            {"description": "Paper too verbose", "category": "writing", "ts": time.time()},
        ]
        overlay = generate_agent_overlay("experimenter", lessons)
        assert overlay == ""  # writing issues not relevant to experimenter

    def test_log_and_load_evolution(self, tmp_path):
        issues = [{"category": "experiment", "description": "test"}]
        log_evolution_event(tmp_path, issues, [], "improving")
        log = load_evolution_log(tmp_path)
        assert len(log) == 1
        assert log[0]["quality_trajectory"] == "improving"


class TestReflectionPostprocess:
    def test_post_reflection_hook(self, tmp_path):
        action_plan = {
            "issues": [
                {"description": "Missing baselines", "category": "experiment"},
                {"description": "Weak introduction", "category": "writing"},
            ]
        }
        result = run_post_reflection_hook(
            tmp_path,
            iteration=1,
            action_plan=action_plan,
            quality_score=7.5,
        )
        assert result["issues_found"] == 2
        assert result["trajectory"] == "insufficient_data"  # only 1 score
        assert result["overlays_generated"] > 0

    def test_deduplication(self, tmp_path):
        issues = [
            {"description": "Missing baselines", "category": "experiment"},
            {"description": "Missing baselines", "category": "experiment"},  # dupe
        ]
        result = run_post_reflection_hook(
            tmp_path, iteration=1,
            action_plan={"issues": issues},
            quality_score=6.0,
        )
        assert result["issues_found"] == 1  # deduped
