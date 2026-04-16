"""Workspace management — filesystem communication hub for all agents."""
from __future__ import annotations
import json
import time
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from tao.orchestration.workspace_paths import (
    resolve_active_root, ensure_workspace_dirs, project_path, active_path,
)


@dataclass
class WorkspaceStatus:
    """Current state of a research workspace."""
    stage: str = "init"
    iteration: int = 0
    errors: list[dict] = field(default_factory=list)
    paused: bool = False
    stop_requested: bool = False
    iteration_dirs: bool = True
    stage_started_at: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceStatus":
        return cls(
            stage=data.get("stage", "init"),
            iteration=data.get("iteration", 0),
            errors=data.get("errors", []),
            paused=data.get("paused", False),
            stop_requested=data.get("stop_requested", False),
            iteration_dirs=data.get("iteration_dirs", True),
            stage_started_at=data.get("stage_started_at"),
        )


class Workspace:
    """Unified filesystem communication backbone for all agents.

    All agents communicate through workspace files (JSON + markdown).
    No direct agent-to-agent messaging — everything goes through workspace,
    enabling fault tolerance and auditability.
    """

    def __init__(self, workspace_root: str | Path, iteration_dirs: bool = True) -> None:
        self._root = Path(workspace_root).resolve()
        self._iteration_dirs = iteration_dirs
        self._status: WorkspaceStatus | None = None

    @property
    def root(self) -> Path:
        """Workspace root directory."""
        return self._root

    @property
    def active_root(self) -> Path:
        """Active working directory (may be iter_NNN/ subdir)."""
        status = self.get_status()
        return resolve_active_root(self._root, status.iteration_dirs, status.iteration)

    def get_status(self) -> WorkspaceStatus:
        """Return current workspace status (cached after first read)."""
        if self._status is not None:
            return self._status
        status_file = self._root / "status.json"
        try:
            with open(status_file, encoding="utf-8") as f:
                data = json.load(f)
            self._status = WorkspaceStatus.from_dict(data)
        except FileNotFoundError:
            self._status = WorkspaceStatus(iteration_dirs=self._iteration_dirs)
        return self._status

    def reload_status(self) -> WorkspaceStatus:
        """Force re-read status from disk (use when external process may have changed it)."""
        self._status = None
        return self.get_status()

    def save_status(self, status: WorkspaceStatus | None = None) -> None:
        """Persist workspace status to disk."""
        if status is not None:
            self._status = status
        if self._status is None:
            return
        self._root.mkdir(parents=True, exist_ok=True)
        with open(self._root / "status.json", "w", encoding="utf-8") as f:
            json.dump(self._status.to_dict(), f, indent=2, ensure_ascii=False)

    def update_stage(self, stage: str) -> None:
        """Advance pipeline stage."""
        status = self.get_status()
        status.stage = stage
        status.stage_started_at = time.time()
        self.save_status(status)

    def update_stage_and_iteration(self, stage: str, iteration: int) -> None:
        """Advance both stage and iteration."""
        status = self.get_status()
        status.stage = stage
        status.iteration = iteration
        status.stage_started_at = time.time()
        self.save_status(status)

    def init_project(self, topic: str, config_yaml: str = "") -> None:
        """Initialize a new research workspace."""
        self._root.mkdir(parents=True, exist_ok=True)
        # Write topic
        self.write_file("topic.txt", topic)
        # Write initial status
        status = WorkspaceStatus(iteration_dirs=self._iteration_dirs)
        self.save_status(status)
        # Write config if provided
        if config_yaml:
            self.write_file("config.yaml", config_yaml)
        # Create directory structure
        ensure_workspace_dirs(self.active_root)

    def read_file(self, relative_path: str) -> str | None:
        """Read a workspace file. Returns None if not found."""
        fp = self._resolve_path(relative_path)
        if fp.exists():
            return fp.read_text(encoding="utf-8")
        return None

    def write_file(self, relative_path: str, content: str) -> Path:
        """Write content to a workspace file. Creates parent dirs."""
        fp = self._resolve_path(relative_path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return fp

    def read_json(self, relative_path: str) -> Any:
        """Read a JSON file from workspace. Returns None if not found."""
        content = self.read_file(relative_path)
        if content is None:
            return None
        return json.loads(content)

    def write_json(self, relative_path: str, data: Any) -> Path:
        """Write data as JSON to workspace file."""
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return self.write_file(relative_path, content)

    def append_file(self, relative_path: str, content: str) -> Path:
        """Append content to a workspace file."""
        fp = self._resolve_path(relative_path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "a", encoding="utf-8") as f:
            f.write(content)
        return fp

    def file_exists(self, relative_path: str) -> bool:
        """Check if a workspace file exists."""
        return self._resolve_path(relative_path).exists()

    def list_files(self, relative_dir: str, pattern: str = "*") -> list[Path]:
        """List files in a workspace directory matching a glob pattern."""
        d = self._resolve_path(relative_dir)
        if not d.is_dir():
            return []
        return sorted(d.glob(pattern))

    def project_path(self, relative: str) -> Path:
        """Get project-scoped path (preserved across iterations)."""
        return project_path(self._root, relative)

    def active_path(self, relative: str) -> Path:
        """Get iteration-scoped path (cleared between iterations)."""
        return active_path(self.active_root, relative)

    def new_iteration(self) -> int:
        """Advance to next iteration. Returns new iteration number."""
        status = self.get_status()
        status.iteration += 1
        status.stage = "init"
        status.stage_started_at = time.time()
        self.save_status(status)
        if status.iteration_dirs:
            ensure_workspace_dirs(self.active_root)
            # Update current symlink
            current_link = self._root / "current"
            if current_link.is_symlink():
                current_link.unlink()
            iter_dir = self.active_root
            current_link.symlink_to(iter_dir.name)
        return status.iteration

    def git_commit(self, message: str) -> bool:
        """Commit workspace changes. Returns True on success."""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self._root), capture_output=True, check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message, "--allow-empty"],
                cwd=str(self._root), capture_output=True, check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def git_tag(self, tag: str, message: str = "") -> bool:
        """Create a git tag. Returns True on success."""
        try:
            cmd = ["git", "tag", tag]
            if message:
                cmd.extend(["-m", message])
            subprocess.run(
                cmd, cwd=str(self._root), capture_output=True, check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def record_error(self, category: str, message: str, details: dict | None = None) -> None:
        """Record an error in workspace status."""
        status = self.get_status()
        status.errors.append({
            "ts": time.time(),
            "category": category,
            "message": message,
            "details": details or {},
        })
        self.save_status(status)

    def clear_iteration_artifacts(self) -> None:
        """Clear ephemeral stage outputs while preserving lessons.

        Preserves: reflection/lessons_learned.md, reflection/action_plan.json
        Clears: idea/, plan/, exp/, writing/, supervisor/, context/
        """
        import shutil
        preserve = {
            "reflection/lessons_learned.md",
            "reflection/action_plan.json",
            "reflection/prev_action_plan.json",
        }
        # Save preserved files
        saved = {}
        for rel in preserve:
            content = self.read_file(rel)
            if content is not None:
                saved[rel] = content

        # Clear directories
        clear_dirs = [
            "idea", "plan", "exp", "writing", "supervisor", "context",
        ]
        for d in clear_dirs:
            dir_path = self.active_root / d
            if dir_path.is_dir():
                shutil.rmtree(dir_path)

        # Recreate structure
        ensure_workspace_dirs(self.active_root)

        # Restore preserved files
        for rel, content in saved.items():
            self.write_file(rel, content)

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path against the active root."""
        return self.active_root / relative_path
