"""Control API for project state transitions."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def pause_project(workspace_root: str | Path) -> dict:
    """Set pause flag on a project."""
    status_file = Path(workspace_root) / "status.json"
    if not status_file.exists():
        return {"success": False, "error": "No status.json"}
    data = json.loads(status_file.read_text())
    data["paused"] = True
    status_file.write_text(json.dumps(data, indent=2))
    return {"success": True, "stage": data.get("stage")}


def resume_project(workspace_root: str | Path) -> dict:
    """Clear pause/stop flags."""
    status_file = Path(workspace_root) / "status.json"
    if not status_file.exists():
        return {"success": False, "error": "No status.json"}
    data = json.loads(status_file.read_text())
    data["paused"] = False
    data["stop_requested"] = False
    status_file.write_text(json.dumps(data, indent=2))
    return {"success": True, "stage": data.get("stage")}


def stop_project(workspace_root: str | Path) -> dict:
    """Set stop flag on a project."""
    status_file = Path(workspace_root) / "status.json"
    if not status_file.exists():
        return {"success": False, "error": "No status.json"}
    data = json.loads(status_file.read_text())
    data["stop_requested"] = True
    status_file.write_text(json.dumps(data, indent=2))
    return {"success": True, "stage": data.get("stage")}
