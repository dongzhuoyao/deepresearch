"""GPU-aware task scheduler for parallel experiment execution."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


def load_task_plan(workspace_root: str | Path) -> dict:
    """Load task_plan.json from workspace.

    Format:
    {
        "tasks": [
            {"id": "train_baseline", "depends_on": [], "gpu_count": 1, "estimated_minutes": 60},
            {"id": "train_main", "depends_on": ["train_baseline"], "gpu_count": 2, "estimated_minutes": 120},
            {"id": "ablation_lr", "depends_on": ["train_baseline"], "gpu_count": 1, "estimated_minutes": 30},
        ]
    }
    """
    plan_file = Path(workspace_root) / "plan" / "task_plan.json"
    if not plan_file.exists():
        return {"tasks": []}
    with open(plan_file, encoding="utf-8") as f:
        return json.load(f)


def load_gpu_progress(workspace_root: str | Path) -> dict:
    """Load GPU progress state.

    Format:
    {
        "running": {"task_id": {"gpu_ids": [0,1], "started_at": 123456}},
        "completed": ["task_id_1", "task_id_2"]
    }
    """
    progress_file = Path(workspace_root) / "exp" / "gpu_progress.json"
    if not progress_file.exists():
        return {"running": {}, "completed": []}
    with open(progress_file, encoding="utf-8") as f:
        return json.load(f)


def save_gpu_progress(workspace_root: str | Path, progress: dict) -> None:
    """Save GPU progress state atomically."""
    progress_file = Path(workspace_root) / "exp" / "gpu_progress.json"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = progress_file.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)
    tmp.rename(progress_file)


def topological_sort(tasks: list[dict]) -> list[str]:
    """Topological sort of tasks based on depends_on.

    Returns ordered list of task IDs.
    Raises ValueError on circular dependencies.
    """
    graph: dict[str, list[str]] = {}
    for task in tasks:
        tid = task["id"]
        deps = task.get("depends_on", [])
        graph[tid] = deps

    # Kahn's algorithm
    in_deg = {tid: 0 for tid in graph}
    for tid, deps in graph.items():
        for dep in deps:
            if dep in in_deg:
                in_deg[tid] += 1  # tid depends on dep

    queue = sorted(tid for tid, deg in in_deg.items() if deg == 0)
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        # Find tasks that depend on this node
        for tid, deps in graph.items():
            if node in deps:
                in_deg[tid] -= 1
                if in_deg[tid] == 0:
                    queue.append(tid)
                    queue.sort()

    if len(result) != len(graph):
        raise ValueError("Circular dependency detected in task plan")

    return result


def get_ready_tasks(tasks: list[dict], progress: dict) -> list[dict]:
    """Get tasks that are ready to run (all deps completed, not running/completed)."""
    completed = set(progress.get("completed", []))
    running = set(progress.get("running", {}).keys())

    ready = []
    for task in tasks:
        tid = task["id"]
        if tid in completed or tid in running:
            continue
        deps = set(task.get("depends_on", []))
        if deps.issubset(completed):
            ready.append(task)
    return ready


def get_next_batch(
    workspace_root: str | Path,
    available_gpu_ids: list[int],
    gpus_per_task: int = 1,
) -> list[dict]:
    """Get the next batch of tasks to dispatch.

    Args:
        workspace_root: Path to workspace
        available_gpu_ids: List of free GPU IDs
        gpus_per_task: GPUs needed per task

    Returns:
        List of {"task_id": str, "gpu_ids": list[int]} assignments
    """
    plan = load_task_plan(workspace_root)
    progress = load_gpu_progress(workspace_root)
    tasks = plan.get("tasks", [])

    if not tasks:
        return []

    ready = get_ready_tasks(tasks, progress)
    if not ready:
        return []

    # Sort by topological order
    try:
        order = topological_sort(tasks)
    except ValueError:
        order = [t["id"] for t in tasks]

    order_map = {tid: i for i, tid in enumerate(order)}
    ready.sort(key=lambda t: order_map.get(t["id"], len(order)))

    # Assign GPUs
    remaining_gpus = list(available_gpu_ids)
    assignments: list[dict] = []

    for task in ready:
        gpu_count = task.get("gpu_count", gpus_per_task)
        if len(remaining_gpus) < gpu_count:
            break
        assigned = remaining_gpus[:gpu_count]
        remaining_gpus = remaining_gpus[gpu_count:]
        assignments.append({
            "task_id": task["id"],
            "gpu_ids": assigned,
        })

    return assignments


def register_running_tasks(workspace_root: str | Path, assignments: list[dict]) -> None:
    """Register dispatched tasks in gpu_progress."""
    progress = load_gpu_progress(workspace_root)
    for assignment in assignments:
        progress["running"][assignment["task_id"]] = {
            "gpu_ids": assignment["gpu_ids"],
            "started_at": time.time(),
        }
    save_gpu_progress(workspace_root, progress)


def mark_task_completed(workspace_root: str | Path, task_id: str) -> None:
    """Mark a task as completed in gpu_progress."""
    progress = load_gpu_progress(workspace_root)
    if task_id in progress["running"]:
        del progress["running"][task_id]
    if task_id not in progress["completed"]:
        progress["completed"].append(task_id)
    save_gpu_progress(workspace_root, progress)


def all_tasks_done(workspace_root: str | Path) -> bool:
    """Check if all tasks in the plan are completed."""
    plan = load_task_plan(workspace_root)
    progress = load_gpu_progress(workspace_root)
    task_ids = {t["id"] for t in plan.get("tasks", [])}
    completed = set(progress.get("completed", []))
    return task_ids.issubset(completed)


def get_progress_summary(workspace_root: str | Path) -> dict:
    """Get a summary of task progress."""
    plan = load_task_plan(workspace_root)
    progress = load_gpu_progress(workspace_root)
    total = len(plan.get("tasks", []))
    completed = len(progress.get("completed", []))
    running = len(progress.get("running", {}))
    pending = total - completed - running
    return {
        "total": total,
        "completed": completed,
        "running": running,
        "pending": pending,
        "completed_ids": progress.get("completed", []),
        "running_ids": list(progress.get("running", {}).keys()),
    }
