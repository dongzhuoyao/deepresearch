"""RunPod-backed experiment launcher for Tao task plans."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from tao.compute.runpod_backend import RunPodBackend
from tao.config import Config
from tao.experiment_recovery import mark_task_dead, mark_task_done, register_dispatched_tasks
from tao.experiment_records import record_experiment
from tao.experiment_tasks import choose_task_script, pending_phase_tasks, write_phase_summary
from tao.gpu_scheduler import mark_task_completed, register_running_tasks


def stage_workspace_bundle(workspace_root: str | Path) -> str:
    """Create a minimal upload bundle containing runtime code and workspace state."""
    workspace_root = Path(workspace_root).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    bundle_dir = Path(tempfile.mkdtemp(prefix="tao-bundle-"))

    for name in ["tao", "scripts"]:
        shutil.copytree(repo_root / name, bundle_dir / name)
    shutil.copy2(repo_root / "pyproject.toml", bundle_dir / "pyproject.toml")

    for child in workspace_root.iterdir():
        target = bundle_dir / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)

    return str(bundle_dir)


def _remote_setup_command(remote_root: str) -> str:
    return " && ".join([
        f"cd {remote_root}",
        "python -m venv .venv",
        ". .venv/bin/activate",
        "python -m pip install --upgrade pip",
        "python -m pip install -e '.[experiment]'",
    ])


def _remote_task_command(remote_root: str, task: dict) -> str:
    script = choose_task_script(task)
    return " && ".join([
        f"cd {remote_root}",
        ". .venv/bin/activate",
        f"python {script} --workspace . --task-id {task['id']}",
    ])


def run_experiment_phase(
    workspace_root: str | Path,
    phase: str,
    keep_pod: bool = False,
) -> dict:
    """Run all pending tasks in a phase sequentially on one RunPod pod."""
    workspace_root = Path(workspace_root).resolve()
    cfg = Config.from_yaml(str(workspace_root / "config.yaml"))
    backend = RunPodBackend.from_config(cfg)
    tasks = pending_phase_tasks(workspace_root, phase)
    summary = write_phase_summary(workspace_root, phase)

    if not tasks:
        return {
            "status": "noop",
            "phase": phase,
            "message": "No pending tasks",
            "summary_file": str(summary),
        }

    pod = backend.create_pod(f"tao-{workspace_root.name}-{phase}")
    pod_id = pod.get("id") or pod.get("podId")
    if not pod_id:
        raise RuntimeError(f"RunPod did not return a pod id: {pod}")
    if not backend.wait_for_ready(pod_id, timeout_sec=900, poll_sec=15):
        raise RuntimeError(f"Pod {pod_id} did not become ready in time")

    remote_root = backend.project_dir(workspace_root.name)
    bundle_dir = stage_workspace_bundle(workspace_root)

    try:
        if not backend.upload_code(pod_id, bundle_dir, remote_root):
            raise RuntimeError("Failed to upload workspace bundle to RunPod")

        setup_result = backend.run_remote(
            pod_id,
            _remote_setup_command(remote_root),
            timeout_sec=3600,
            use_tmux=True,
            session_name="tao_setup",
        )
        if setup_result["returncode"] != 0:
            raise RuntimeError(f"Remote setup failed: {setup_result['stderr'] or setup_result['stdout']}")

        executed = []
        for task in tasks:
            assignment = {"task_id": task["id"], "gpu_ids": list(range(task.get("gpu_count", 1)))}
            register_running_tasks(workspace_root, [assignment])
            register_dispatched_tasks(workspace_root, [assignment])

            result = backend.run_remote(
                pod_id,
                _remote_task_command(remote_root, task),
                timeout_sec=int(task.get("timeout_minutes", 60)) * 60,
                use_tmux=True,
                session_name=f"tao_{task['id']}",
            )
            if result["returncode"] != 0:
                mark_task_dead(workspace_root, task["id"], reason=result["stderr"] or result["stdout"])
                raise RuntimeError(f"Task {task['id']} failed: {result['stderr'] or result['stdout']}")

            local_results_dir = workspace_root / "exp" / "results" / task["id"]
            backend.download_results(
                pod_id,
                f"{remote_root}/exp/results/{task['id']}",
                str(local_results_dir),
            )

            result_file = local_results_dir / "result.json"
            if result_file.exists():
                task_result = json.loads(result_file.read_text(encoding="utf-8"))
                record_experiment(
                    workspace_root,
                    task_id=task["id"],
                    config=task,
                    results=task_result,
                    metrics=task_result.get("metrics", {}),
                    metadata={"phase": phase, "pod_id": pod_id},
                )

            mark_task_completed(workspace_root, task["id"])
            mark_task_done(workspace_root, task["id"])
            executed.append(task["id"])

        return {
            "status": "success",
            "phase": phase,
            "pod_id": pod_id,
            "executed_tasks": executed,
            "summary_file": str(summary),
        }
    finally:
        shutil.rmtree(bundle_dir, ignore_errors=True)
        if not keep_pod:
            try:
                backend.terminate_pod(pod_id)
            except Exception:
                pass
