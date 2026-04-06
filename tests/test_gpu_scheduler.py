"""Tests for GPU scheduler."""
import json
from pathlib import Path
from tao.gpu_scheduler import (
    load_task_plan, load_gpu_progress, save_gpu_progress,
    topological_sort, get_ready_tasks, get_next_batch,
    register_running_tasks, mark_task_completed,
    all_tasks_done, get_progress_summary,
)


def _write_plan(tmp_path, tasks):
    (tmp_path / "plan").mkdir(parents=True, exist_ok=True)
    with open(tmp_path / "plan" / "task_plan.json", "w") as f:
        json.dump({"tasks": tasks}, f)


def _write_progress(tmp_path, progress):
    (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
    with open(tmp_path / "exp" / "gpu_progress.json", "w") as f:
        json.dump(progress, f)


class TestTaskPlan:
    def test_load_empty(self, tmp_path):
        plan = load_task_plan(tmp_path)
        assert plan["tasks"] == []

    def test_load_plan(self, tmp_path):
        tasks = [
            {"id": "baseline", "depends_on": [], "gpu_count": 1},
            {"id": "main", "depends_on": ["baseline"], "gpu_count": 2},
        ]
        _write_plan(tmp_path, tasks)
        plan = load_task_plan(tmp_path)
        assert len(plan["tasks"]) == 2


class TestTopologicalSort:
    def test_no_deps(self):
        tasks = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        order = topological_sort(tasks)
        assert set(order) == {"a", "b", "c"}

    def test_linear_deps(self):
        tasks = [
            {"id": "a", "depends_on": []},
            {"id": "b", "depends_on": ["a"]},
            {"id": "c", "depends_on": ["b"]},
        ]
        order = topological_sort(tasks)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_deps(self):
        tasks = [
            {"id": "a", "depends_on": []},
            {"id": "b", "depends_on": ["a"]},
            {"id": "c", "depends_on": ["a"]},
            {"id": "d", "depends_on": ["b", "c"]},
        ]
        order = topological_sort(tasks)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_circular_raises(self):
        tasks = [
            {"id": "a", "depends_on": ["b"]},
            {"id": "b", "depends_on": ["a"]},
        ]
        import pytest
        with pytest.raises(ValueError, match="Circular"):
            topological_sort(tasks)


class TestGetReadyTasks:
    def test_all_ready(self):
        tasks = [{"id": "a"}, {"id": "b"}]
        ready = get_ready_tasks(tasks, {"running": {}, "completed": []})
        assert len(ready) == 2

    def test_deps_not_met(self):
        tasks = [
            {"id": "a", "depends_on": []},
            {"id": "b", "depends_on": ["a"]},
        ]
        ready = get_ready_tasks(tasks, {"running": {}, "completed": []})
        assert len(ready) == 1
        assert ready[0]["id"] == "a"

    def test_deps_met(self):
        tasks = [
            {"id": "a", "depends_on": []},
            {"id": "b", "depends_on": ["a"]},
        ]
        ready = get_ready_tasks(tasks, {"running": {}, "completed": ["a"]})
        assert len(ready) == 1
        assert ready[0]["id"] == "b"

    def test_skip_running(self):
        tasks = [{"id": "a"}, {"id": "b"}]
        ready = get_ready_tasks(tasks, {"running": {"a": {}}, "completed": []})
        assert len(ready) == 1
        assert ready[0]["id"] == "b"


class TestGetNextBatch:
    def test_basic_assignment(self, tmp_path):
        _write_plan(tmp_path, [
            {"id": "a", "depends_on": [], "gpu_count": 1},
            {"id": "b", "depends_on": [], "gpu_count": 1},
        ])
        batch = get_next_batch(tmp_path, [0, 1])
        assert len(batch) == 2
        assert batch[0]["task_id"] == "a"
        assert batch[1]["task_id"] == "b"

    def test_not_enough_gpus(self, tmp_path):
        _write_plan(tmp_path, [
            {"id": "a", "depends_on": [], "gpu_count": 2},
            {"id": "b", "depends_on": [], "gpu_count": 2},
        ])
        batch = get_next_batch(tmp_path, [0, 1])
        assert len(batch) == 1  # Only one task can fit

    def test_empty_plan(self, tmp_path):
        batch = get_next_batch(tmp_path, [0, 1])
        assert batch == []


class TestProgressTracking:
    def test_register_and_complete(self, tmp_path):
        (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
        register_running_tasks(tmp_path, [{"task_id": "a", "gpu_ids": [0]}])
        progress = load_gpu_progress(tmp_path)
        assert "a" in progress["running"]

        mark_task_completed(tmp_path, "a")
        progress = load_gpu_progress(tmp_path)
        assert "a" not in progress["running"]
        assert "a" in progress["completed"]

    def test_all_tasks_done(self, tmp_path):
        _write_plan(tmp_path, [{"id": "a"}, {"id": "b"}])
        _write_progress(tmp_path, {"running": {}, "completed": ["a", "b"]})
        assert all_tasks_done(tmp_path) is True

    def test_not_all_done(self, tmp_path):
        _write_plan(tmp_path, [{"id": "a"}, {"id": "b"}])
        _write_progress(tmp_path, {"running": {}, "completed": ["a"]})
        assert all_tasks_done(tmp_path) is False

    def test_progress_summary(self, tmp_path):
        _write_plan(tmp_path, [{"id": "a"}, {"id": "b"}, {"id": "c"}])
        _write_progress(tmp_path, {"running": {"b": {"gpu_ids": [0]}}, "completed": ["a"]})
        summary = get_progress_summary(tmp_path)
        assert summary["total"] == 3
        assert summary["completed"] == 1
        assert summary["running"] == 1
        assert summary["pending"] == 1
