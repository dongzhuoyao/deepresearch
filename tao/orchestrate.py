"""Main orchestrator — the API surface for the research pipeline."""
from __future__ import annotations
import dataclasses
import json
from pathlib import Path
from typing import Any

from tao.config import Config
from tao.evolution import load_evolution_log
from tao.workspace import Workspace
from tao.orchestration.lifecycle import Lifecycle
from tao.orchestration.action_dispatcher import render_execution_script
from tao.orchestration.prompt_loader import compile_prompt
from tao.experiment_launcher import run_experiment_phase


class FarsOrchestrator:
    """State-machine orchestrator for the research pipeline.

    Sits at the heart of the system. Generates deterministic actions
    for the main Claude Code session to execute.
    """

    def __init__(self, workspace_path: str | Path, config: Config | None = None) -> None:
        self._cfg = config or Config()
        self._ws = Workspace(Path(workspace_path).resolve(), iteration_dirs=self._cfg.iteration_dirs)
        self._lifecycle = Lifecycle(self._ws, self._cfg)

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
        return str(self._ws.root)

    def get_next_action(self) -> dict:
        """Get the next action as a JSON-serializable dict."""
        action = self._lifecycle.get_next_action()
        render_execution_script(action)
        return dataclasses.asdict(action)

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


def cli_experiment_run(workspace_path: str, phase: str, keep_pod: bool = False) -> str:
    """Run a pilot or full experiment phase and return the launcher summary."""
    result = run_experiment_phase(workspace_path, phase, keep_pod=keep_pod)
    return json.dumps(result, indent=2, ensure_ascii=False)


def cli_evolve(arguments: str = ".") -> str:
    """Manage evolution log from the orchestration API."""
    args = (arguments or ".").strip()
    workspace = "."
    mode = "--show"
    for token in args.split():
        if token.startswith("--"):
            mode = token
        elif token:
            workspace = token

    log_file = Path(workspace) / "logs" / "evolution_log.jsonl"

    if mode == "--reset":
        if log_file.exists():
            log_file.unlink()
        return "Evolution history reset"

    entries = load_evolution_log(workspace)
    if not entries:
        return "No evolution history found"

    if mode == "--apply":
        return "Evolution overlays are generated lazily from the existing log in this build."

    lines = []
    for entry in entries[-10:]:
        quality = entry.get("quality_trajectory", "unknown")
        issues = entry.get("issues_count", 0)
        fixes = entry.get("fixes_count", 0)
        lines.append(f"[{quality}] issues={issues} fixes={fixes}")
    return "\n".join(lines)


def cli_init(
    topic: str,
    config_path: str = "",
    workspace_dir: str = "",
    workspace_name: str = "",
) -> str:
    """Initialize a new project. Returns workspace path."""
    if config_path:
        cfg = Config.from_yaml(config_path)
    else:
        cfg = Config()

    if workspace_dir:
        ws_dir = Path(workspace_dir)
    else:
        ws_dir = cfg.workspaces_dir

    ws_name = _sanitize_workspace_name(workspace_name) if workspace_name else _topic_to_name(topic)
    ws_path = ws_dir / ws_name

    orch = FarsOrchestrator(ws_path, cfg)
    return orch.init_project(topic)


def cli_init_from_spec(
    spec_path: str,
    config_path: str = "",
    workspace_dir: str = "",
    workspace_name: str = "",
) -> str:
    """Initialize project from a spec.md file. Returns workspace path."""
    spec = Path(spec_path).read_text(encoding="utf-8")
    # Extract topic from first heading or first line
    topic = spec.split("\n")[0].strip().lstrip("#").strip()
    if not topic:
        topic = "research_project"

    ws_path = cli_init(topic, config_path, workspace_dir, workspace_name)

    # Copy spec into workspace
    ws = Workspace(ws_path, iteration_dirs=True)
    ws.write_file("spec.md", spec)

    return ws_path


def render_skill_prompt(workspace_path: str, skill_name: str) -> str:
    """Render a compiled prompt for a skill. Called by skill shebangs."""
    ws_path = Path(workspace_path).resolve()
    config_file = ws_path / "config.yaml"
    cfg = Config.from_yaml(str(config_file)) if config_file.exists() else Config()
    ws = Workspace(ws_path, iteration_dirs=cfg.iteration_dirs)
    agent_name = _skill_to_agent_name(skill_name)
    extra_context = "\n".join([
        "## Runtime Contract",
        f"- Active workspace root: `{ws_path}`",
        "- Use repository CLI entrypoints and workspace files as the source of truth.",
        "- Do not rely on host-specific slash commands when a Python or shell command is available.",
    ])
    return compile_prompt(agent_name, ws, cfg, extra_context=extra_context)


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


def _sanitize_workspace_name(name: str) -> str:
    """Normalize a user-chosen workspace folder name to a filesystem-safe form."""
    import re
    cleaned = name.strip().lower().replace(" ", "_").replace("-", "_")
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
    cleaned = cleaned[:80]
    if not cleaned:
        raise ValueError(f"Invalid workspace name: {name!r}")
    return cleaned


def _skill_to_agent_name(skill_name: str) -> str:
    """Map a public skill identifier to the underlying prompt name."""
    normalized = skill_name.strip()
    explicit_mappings = {
        "experiment-supervisor": "experiment_supervisor",
        "final-critic": "final_critic",
        "idea-validation-decision": "idea_validation_decision",
        "latex-writer": "latex_writer",
        "literature": "literature_researcher",
        "novelty-checker": "novelty_checker",
        "outline-writer": "outline_writer",
        "result-synthesizer": "result_synthesizer",
        "section-critic": "section_critic",
        "section-writer": "section_writer",
        "self-healer": "self_healer",
        "sequential-writer": "sequential_writer",
        "simulated-reviewer": "simulated_reviewer",
        "supervisor-decision": "supervisor_decision",
    }
    return explicit_mappings.get(normalized, normalized.replace("-", "_"))
