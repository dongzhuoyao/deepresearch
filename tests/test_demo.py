"""Tests for demo smoke test."""
from tao.demo import run_demo


def test_demo_runs(tmp_path):
    results = run_demo(output_dir=tmp_path)
    assert results["actions_generated"] > 0
    assert len(results["stages_visited"]) > 5
    assert results["all_checks_passed"] is True
    assert len(results["errors"]) == 0
    assert "done" in results["stages_visited"]
