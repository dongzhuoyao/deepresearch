"""Main orchestrator — the API surface for the research pipeline."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from tao.config import Config
from tao.workspace import Workspace
from tao.orchestration.lifecycle import Lifecycle
from tao.orchestration.action_dispatcher import render_execution_script
from tao.orchestration.state_machine import StateMachine


class FarsOrchestrator:
    """State-machine orchestrator for the research pipeline.

    Sits at the heart of the system. Generates deterministic actions
    for the main Claude Code session to execute.
    """

    def __init__(self, workspace_path: str | Path, config: Config | None = None) -> None:
        self._ws_path = Path(workspace_path).resolve()
        self._cfg = config or Config()
        self._ws = Workspace(self._ws_path, iteration_dirs=self._cfg.iteration_dirs)
        self._lifecycle = Lifecycle(self._ws, self._cfg)
        self._sm = StateMachine(self._ws, self._cfg)

    @property
    def workspace(self) -> Workspace:
        return self._ws

    @property
    def config(self) -> Config:
        return self._cfg

    def init_project(self, topic: str) -> str:
        """Initialize a new research project.

        Returns the workspace path.
        """
        self._ws.init_project(topic, self._cfg.to_yaml())
        return str(self._ws_path)

    def get_next_action(self) -> dict:
        """Get the next action as a JSON-serializable dict."""
        action = self._lifecycle.get_next_action()
        render_execution_script(action)
        return {
            "action_type": action.action_type,
            "stage": action.stage,
            "iteration": action.iteration,
            "description": action.description,
            "estimated_minutes": action.estimated_minutes,
            "execution_script": action.execution_script,
            "skills": action.skills,
            "agents": action.agents,
            "team": action.team,
            "bash_command": action.bash_command,
            "experiment_monitor": action.experiment_monitor,
        }

    def record_result(self, stage: str, result: str, score: float = 0.0) -> str:
        """Record stage result and advance. Returns next stage."""
        return self._lifecycle.record_result(stage, result, score)

    def get_status(self) -> dict:
        """Get current workspace status as dict."""
        status = self._ws.get_status()
        return status.to_dict()

    def is_done(self) -> bool:
        """Check if the pipeline is done."""
        status = self._ws.get_status()
        return status.stage == "done"


# --- CLI-callable functions ---
# These are called from plugin commands and the CLI.

def cli_next(workspace_path: str) -> str:
    """Get next action as JSON string. Called by plugin commands."""
    orch = _load_orchestrator(workspace_path)
    action = orch.get_next_action()
    return json.dumps(action, indent=2, ensure_ascii=False)


def cli_record(workspace_path: str, stage: str, result: str, score: float = 0.0) -> str:
    """Record result and return next stage. Called by plugin commands."""
    orch = _load_orchestrator(workspace_path)
    next_stage = orch.record_result(stage, result, score)
    return json.dumps({"next_stage": next_stage, "stage": stage, "score": score})


def cli_status(workspace_path: str) -> str:
    """Get workspace status as JSON string."""
    orch = _load_orchestrator(workspace_path)
    return json.dumps(orch.get_status(), indent=2, ensure_ascii=False)


def cli_init(topic: str, config_path: str = "", workspace_dir: str = "") -> str:
    """Initialize a new project. Returns workspace path."""
    if config_path:
        cfg = Config.from_yaml(config_path)
    else:
        cfg = Config()

    if workspace_dir:
        ws_dir = Path(workspace_dir)
    else:
        ws_dir = cfg.workspaces_dir

    # Generate workspace name from topic
    ws_name = _topic_to_name(topic)
    ws_path = ws_dir / ws_name

    orch = FarsOrchestrator(ws_path, cfg)
    return orch.init_project(topic)


def cli_init_from_spec(spec_path: str, config_path: str = "", workspace_dir: str = "") -> str:
    """Initialize project from a spec.md file. Returns workspace path."""
    spec = Path(spec_path).read_text(encoding="utf-8")
    # Extract topic from first heading or first line
    topic = spec.split("\n")[0].strip().lstrip("#").strip()
    if not topic:
        topic = "research_project"

    ws_path = cli_init(topic, config_path, workspace_dir)

    # Copy spec into workspace
    ws = Workspace(ws_path, iteration_dirs=True)
    ws.write_file("spec.md", spec)

    return ws_path


def render_skill_prompt(workspace_path: str, skill_name: str) -> str:
    """Render a compiled prompt for a skill. Called by skill shebangs."""
    # Will be fully implemented when prompt_loader is ready
    ws = Workspace(workspace_path)
    topic = ws.read_file("topic.txt") or "research"
    return f"You are {skill_name} working on: {topic}"


def _load_orchestrator(workspace_path: str) -> FarsOrchestrator:
    """Load orchestrator from workspace, reading config if available."""
    ws_path = Path(workspace_path).resolve()
    config_file = ws_path / "config.yaml"
    if config_file.exists():
        cfg = Config.from_yaml(str(config_file))
    else:
        cfg = Config()
    return FarsOrchestrator(ws_path, cfg)


def _topic_to_name(topic: str) -> str:
    """Convert a research topic to a filesystem-safe workspace name."""
    import re
    import time
    # Take first few words, lowercase, replace spaces with underscores
    words = topic.lower().split()[:5]
    name = "_".join(words)
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = name[:50]  # cap length
    # Add timestamp for uniqueness
    ts = int(time.time()) % 100000
    return f"{name}_{ts}"
