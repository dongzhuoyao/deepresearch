"""Experiment crash recovery and state management."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from tao._io import atomic_write_json


@dataclass
class TaskState:
    """State of a single experiment task."""
    status: str = "pending"  # pending, running, done, dead, unknown
    gpu_ids: list[int] = field(default_factory=list)
    pid_file: str = ""
    registered_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class ExperimentState:
    """Overall experiment state for a workspace."""
    schema_version: int = 1
    tasks: dict[str, dict] = field(default_factory=dict)
    last_recovery_at: str = ""
    recovery_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentState":
        return cls(
            schema_version=data.get("schema_version", 1),
            tasks=data.get("tasks", {}),
            last_recovery_at=data.get("last_recovery_at", ""),
            recovery_log=data.get("recovery_log", []),
        )


def load_experiment_state(workspace_root: str | Path) -> ExperimentState:
    """Load experiment state from workspace."""
    state_file = Path(workspace_root) / "exp" / "experiment_state.json"
    if not state_file.exists():
        return ExperimentState()
    with open(state_file, encoding="utf-8") as f:
        return ExperimentState.from_dict(json.load(f))


def save_experiment_state(workspace_root: str | Path, state: ExperimentState) -> None:
    """Save experiment state atomically."""
    atomic_write_json(Path(workspace_root) / "exp" / "experiment_state.json", state.to_dict())


def register_dispatched_tasks(
    workspace_root: str | Path,
    assignments: list[dict],
) -> None:
    """Register newly dispatched tasks in experiment state."""
    state = load_experiment_state(workspace_root)
    for assignment in assignments:
        task_id = assignment["task_id"]
        state.tasks[task_id] = {
            "status": "running",
            "gpu_ids": assignment.get("gpu_ids", []),
            "registered_at": time.time(),
        }
    save_experiment_state(workspace_root, state)


def mark_task_done(workspace_root: str | Path, task_id: str) -> None:
    """Mark a task as done in experiment state."""
    state = load_experiment_state(workspace_root)
    if task_id in state.tasks:
        state.tasks[task_id]["status"] = "done"
        state.tasks[task_id]["completed_at"] = time.time()
    save_experiment_state(workspace_root, state)


def mark_task_dead(workspace_root: str | Path, task_id: str, reason: str = "") -> None:
    """Mark a task as dead (crashed) in experiment state."""
    state = load_experiment_state(workspace_root)
    if task_id in state.tasks:
        state.tasks[task_id]["status"] = "dead"
        state.tasks[task_id]["death_reason"] = reason
    state.recovery_log.append({
        "ts": time.time(),
        "task_id": task_id,
        "event": "marked_dead",
        "reason": reason,
    })
    save_experiment_state(workspace_root, state)


def sync_completed_from_progress(workspace_root: str | Path) -> list[str]:
    """Sync completed tasks from gpu_progress.json to experiment_state.json.

    Returns list of newly synced task IDs.
    """
    from tao.gpu_scheduler import load_gpu_progress

    progress = load_gpu_progress(workspace_root)
    state = load_experiment_state(workspace_root)

    synced = []
    for task_id in progress.get("completed", []):
        if task_id in state.tasks and state.tasks[task_id].get("status") != "done":
            state.tasks[task_id]["status"] = "done"
            state.tasks[task_id]["completed_at"] = time.time()
            synced.append(task_id)
        elif task_id not in state.tasks:
            state.tasks[task_id] = {"status": "done", "completed_at": time.time()}
            synced.append(task_id)

    if synced:
        save_experiment_state(workspace_root, state)
    return synced


def generate_detection_script(project_dir: str, task_ids: list[str]) -> str:
    """Generate bash script to detect task status on RunPod pod.

    For each task, checks:
    - DONE marker exists -> DONE:task_id
    - PID file exists + process alive -> RUNNING:task_id
    - PID file exists + process dead -> DEAD:task_id
    - Neither -> UNKNOWN:task_id
    """
    task_ids_str = " ".join(f'"{t}"' for t in task_ids)
    return f'''#!/bin/bash
PROJECT_DIR="{project_dir}"
TASK_IDS=({task_ids_str})

for tid in "${{TASK_IDS[@]}}"; do
    if [ -f "$PROJECT_DIR/${{tid}}_DONE" ]; then
        # Read result JSON if available
        RESULT=""
        if [ -f "$PROJECT_DIR/${{tid}}_result.json" ]; then
            RESULT=$(cat "$PROJECT_DIR/${{tid}}_result.json")
        fi
        echo "DONE:$tid:$RESULT"
    elif [ -f "$PROJECT_DIR/${{tid}}.pid" ]; then
        PID=$(cat "$PROJECT_DIR/${{tid}}.pid")
        if kill -0 "$PID" 2>/dev/null; then
            PROGRESS=""
            if [ -f "$PROJECT_DIR/${{tid}}_PROGRESS.json" ]; then
                PROGRESS=$(cat "$PROJECT_DIR/${{tid}}_PROGRESS.json")
            fi
            echo "RUNNING:$tid:$PROGRESS"
        else
            echo "DEAD:$tid:$PID"
        fi
    else
        echo "UNKNOWN:$tid"
    fi
done
'''


def get_experiment_summary(workspace_root: str | Path) -> dict:
    """Get summary of experiment state."""
    state = load_experiment_state(workspace_root)
    counts = {"pending": 0, "running": 0, "done": 0, "dead": 0, "unknown": 0}
    for task_info in state.tasks.values():
        status = task_info.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": len(state.tasks),
        "counts": counts,
        "recovery_events": len(state.recovery_log),
    }
