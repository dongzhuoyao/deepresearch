"""Tests for experiment recovery, records, and digest."""
import json
from pathlib import Path
from tao.experiment_recovery import (
    ExperimentState, load_experiment_state, save_experiment_state,
    register_dispatched_tasks, mark_task_done, mark_task_dead,
    sync_completed_from_progress, generate_detection_script,
    get_experiment_summary,
)
from tao.experiment_records import record_experiment, load_experiments, get_best_result
from tao.experiment_digest import generate_digest


class TestExperimentState:
    def test_defaults(self):
        state = ExperimentState()
        assert state.schema_version == 1
        assert state.tasks == {}

    def test_roundtrip(self):
        state = ExperimentState(tasks={"a": {"status": "running"}})
        d = state.to_dict()
        state2 = ExperimentState.from_dict(d)
        assert state2.tasks["a"]["status"] == "running"


class TestExperimentRecovery:
    def test_register_and_mark_done(self, tmp_path):
        (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
        register_dispatched_tasks(tmp_path, [
            {"task_id": "a", "gpu_ids": [0]},
            {"task_id": "b", "gpu_ids": [1]},
        ])
        state = load_experiment_state(tmp_path)
        assert state.tasks["a"]["status"] == "running"

        mark_task_done(tmp_path, "a")
        state = load_experiment_state(tmp_path)
        assert state.tasks["a"]["status"] == "done"

    def test_mark_dead(self, tmp_path):
        (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
        register_dispatched_tasks(tmp_path, [{"task_id": "a", "gpu_ids": [0]}])
        mark_task_dead(tmp_path, "a", "OOM killed")
        state = load_experiment_state(tmp_path)
        assert state.tasks["a"]["status"] == "dead"
        assert len(state.recovery_log) == 1

    def test_sync_from_progress(self, tmp_path):
        (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
        # Write gpu_progress with completed task
        with open(tmp_path / "exp" / "gpu_progress.json", "w") as f:
            json.dump({"running": {}, "completed": ["a", "b"]}, f)
        register_dispatched_tasks(tmp_path, [{"task_id": "a", "gpu_ids": [0]}])
        synced = sync_completed_from_progress(tmp_path)
        assert "a" in synced
        state = load_experiment_state(tmp_path)
        assert state.tasks["a"]["status"] == "done"

    def test_detection_script(self):
        script = generate_detection_script("/workspace/proj", ["train_a", "train_b"])
        assert "train_a" in script
        assert "_DONE" in script
        assert ".pid" in script
        assert "DEAD" in script

    def test_summary(self, tmp_path):
        (tmp_path / "exp").mkdir(parents=True, exist_ok=True)
        register_dispatched_tasks(tmp_path, [
            {"task_id": "a", "gpu_ids": [0]},
            {"task_id": "b", "gpu_ids": [1]},
        ])
        mark_task_done(tmp_path, "a")
        summary = get_experiment_summary(tmp_path)
        assert summary["total"] == 2
        assert summary["counts"]["done"] == 1
        assert summary["counts"]["running"] == 1


class TestExperimentRecords:
    def test_record_and_load(self, tmp_path):
        record_experiment(tmp_path, "baseline", {"lr": 0.001}, {"loss": 0.5}, {"accuracy": 0.85})
        record_experiment(tmp_path, "main", {"lr": 0.01}, {"loss": 0.3}, {"accuracy": 0.92})
        records = load_experiments(tmp_path)
        assert len(records) == 2

    def test_load_filtered(self, tmp_path):
        record_experiment(tmp_path, "a", {}, {})
        record_experiment(tmp_path, "b", {}, {})
        records = load_experiments(tmp_path, task_id="a")
        assert len(records) == 1

    def test_best_result(self, tmp_path):
        record_experiment(tmp_path, "a", {}, {}, {"acc": 0.85})
        record_experiment(tmp_path, "b", {}, {}, {"acc": 0.92})
        record_experiment(tmp_path, "c", {}, {}, {"acc": 0.88})
        best = get_best_result(tmp_path, "acc")
        assert best["task_id"] == "b"

    def test_best_result_lower_better(self, tmp_path):
        record_experiment(tmp_path, "a", {}, {}, {"loss": 0.5})
        record_experiment(tmp_path, "b", {}, {}, {"loss": 0.2})
        best = get_best_result(tmp_path, "loss", higher_is_better=False)
        assert best["task_id"] == "b"

    def test_load_empty(self, tmp_path):
        records = load_experiments(tmp_path)
        assert records == []


class TestExperimentDigest:
    def test_empty(self, tmp_path):
        digest = generate_digest(tmp_path)
        assert "No experiments" in digest

    def test_with_records(self, tmp_path):
        record_experiment(tmp_path, "baseline", {"lr": 0.001}, {"loss": 0.5}, {"acc": 0.85})
        digest = generate_digest(tmp_path)
        assert "baseline" in digest
        assert "acc" in digest


def test_run_experiment_phase_wraps_in_tmux(tmp_path, monkeypatch):
    """experiment_launcher should pass use_tmux=True to run_remote."""
    from tao import experiment_launcher as el

    # Minimal workspace with one pending task
    ws = tmp_path
    (ws / "exp" / "code").mkdir(parents=True)
    (ws / "exp" / "results").mkdir(parents=True)
    (ws / "exp" / "tasks.json").write_text(
        '[{"id":"t1","phase":"pilot","script":"echo.py","gpu_count":1,"timeout_minutes":1}]'
    )

    captured_calls = []

    class FakeBackend:
        def __init__(self, *a, **k):
            pass

        @classmethod
        def from_config(cls, *a, **k):
            return cls()

        def ensure_pod(self, *a, **k):
            return {"pod_id": "p", "remote_root": "/r"}

        def create_pod(self, *a, **k):
            return {"id": "p"}

        def wait_for_ready(self, *a, **k):
            return True

        def project_dir(self, name):
            return f"/workspace/{name}"

        def upload_code(self, *a, **k):
            return True

        def run_remote(self, pod_id, command, **kw):
            captured_calls.append(kw)
            return {"stdout": "", "stderr": "", "returncode": 0}

        def download_results(self, *a, **k):
            return True

        def terminate_pod(self, *a, **k):
            pass

        def stop_pod(self, *a, **k):
            pass

        def get_pod_ssh_info(self, *a, **k):
            return {"mode": "basic"}

    monkeypatch.setattr(el, "RunPodBackend", FakeBackend)

    # Stub inner helpers that touch the filesystem hard
    monkeypatch.setattr(el, "stage_workspace_bundle", lambda w: str(tmp_path))
    monkeypatch.setattr(el, "choose_task_script", lambda t: "echo.py")
    monkeypatch.setattr(el, "pending_phase_tasks", lambda w, p: [
        {"id": "t1", "phase": "pilot", "script": "echo.py", "gpu_count": 1, "timeout_minutes": 1}
    ])
    monkeypatch.setattr(el, "write_phase_summary", lambda w, p: tmp_path / "summary.md")
    # Avoid requiring a real config.yaml
    from tao.config import Config
    monkeypatch.setattr(el.Config, "from_yaml", classmethod(lambda cls, p: Config()))

    try:
        el.run_experiment_phase(ws, phase="pilot")
    except Exception:
        pass  # test cares only that run_remote was called with use_tmux

    assert captured_calls, "run_remote was not called"
    assert all(c.get("use_tmux") is True for c in captured_calls)
