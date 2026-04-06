# Tao-Style Full Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign deepresearch as a full mirror of the SibylSystem architecture — 19-stage pipeline with deterministic state machine, multi-agent teams, RunPod-only compute backend, GPU scheduler, workspace-as-communication-hub, self-healing, prompt evolution, plugin system, WebUI, and rebuttal pipeline.

**Architecture:** Replace the current 8-stage linear pipeline with SibylSystem's dual-loop architecture: an inner research iteration loop (literature → idea debate → planning → pilot → experiment → writing → review → quality gate → loop) and an outer self-evolution loop (issue classification → lesson extraction → prompt overlay injection). All compute runs exclusively on RunPod GPU pods via their API + SSH.

**Tech Stack:** Python 3.11+, PyYAML, Rich, Flask + flask-sock (WebUI), RunPod API (runpod python SDK), SSH (paramiko or subprocess), Claude Code native (agents/skills/plugins), asyncio, watchfiles.

---

## Phase 1: Foundation — Strip & Restructure

### Task 1.1: Clean Slate — New Package Structure

**Files:**
- Delete: `src/deepresearch/` (entire old package — preserved on `python` branch)
- Create: `sibyl/` (new top-level package, matching SibylSystem)

Create the new directory skeleton:

```
sibyl/
├── __init__.py
├── _paths.py
├── config.py
├── workspace.py
├── orchestrate.py
├── event_logger.py
├── error_collector.py
├── compute/
│   ├── __init__.py
│   ├── base.py
│   └── runpod_backend.py
├── orchestration/
│   ├── __init__.py
│   ├── models.py
│   ├── constants.py
│   ├── state_machine.py
│   ├── lifecycle.py
│   ├── action_dispatcher.py
│   ├── prompt_loader.py
│   ├── context_builder.py
│   ├── config_helpers.py
│   ├── common_utils.py
│   ├── workspace_paths.py
│   ├── simple_actions.py
│   ├── team_actions.py
│   ├── experiment_actions.py
│   ├── writing_artifacts.py
│   ├── review_artifacts.py
│   ├── reflection_postprocess.py
│   ├── checkpointing.py
│   ├── dashboard_data.py
│   ├── cli_core.py
│   ├── project_cli.py
│   ├── runtime_cli.py
│   ├── ops_cli.py
│   └── migration_cli.py
├── gpu_scheduler.py
├── experiment_recovery.py
├── experiment_records.py
├── experiment_digest.py
├── auto_fix.py
├── self_heal.py
├── reflection.py
├── evolution.py
├── runtime_assets.py
├── orchestra_skills.py
├── lark_sync.py
├── lark_markdown_converter.py
├── latex_pipeline.py
├── demo.py
├── cli.py
├── prompts/           (markdown prompt templates)
├── dashboard/
│   ├── __init__.py
│   └── server.py
├── webui/
│   ├── __init__.py
│   ├── app.py
│   ├── control_api.py
│   ├── monitor_api.py
│   ├── session_registry.py
│   ├── state_watcher.py
│   ├── conversation_watcher.py
│   ├── message_injector.py
│   └── ws_hub.py
└── rebuttal/
    ├── __init__.py
    ├── orchestrator.py
    ├── actions.py
    ├── cli.py
    ├── config.py
    ├── constants.py
    ├── prompt_helpers.py
    ├── scoring.py
    ├── state_machine.py
    └── workspace_setup.py
```

Also create:
```
plugin/
├── .claude-plugin/
├── commands/         (markdown CLI commands)
└── hooks/
    └── scripts/
```

**Step 1:** Delete old src/ directory

```bash
rm -rf src/deepresearch
rmdir src  # if empty
```

**Step 2:** Create all directories

```bash
mkdir -p sibyl/{compute,orchestration,prompts,dashboard,webui,rebuttal}
mkdir -p plugin/{.claude-plugin,commands,hooks/scripts}
mkdir -p tests
```

**Step 3:** Create all `__init__.py` files

```python
# sibyl/__init__.py
"""Tao Research System — Autonomous AI Scientist."""
__version__ = "1.0.0"
```

Create empty `__init__.py` in each sub-package.

**Step 4:** Update pyproject.toml

```toml
[project]
name = "deepresearch"
version = "1.0.0"
description = "Tao Research System — Autonomous AI Scientist (RunPod Native)"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "rich>=13.0",
    "flask>=3.0",
    "gunicorn>=22.0",
    "flask-sock>=0.7",
    "watchfiles>=0.21",
    "runpod>=1.7.0",
    "paramiko>=3.4.0",
]

[project.optional-dependencies]
lark = ["lark-oapi>=1.0.0", "mistune>=3.0"]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]

[project.scripts]
sibyl = "sibyl.cli:main"
deepresearch = "sibyl.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["sibyl"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["workspaces", ".git", ".venv"]
```

**Step 5:** Commit

```bash
git add -A
git commit -m "chore: restructure to sibyl architecture (strip old src/)"
```

---

### Task 1.2: Core Models & Constants

**Files:**
- Create: `sibyl/orchestration/models.py`
- Create: `sibyl/orchestration/constants.py`

**Step 1:** Write models.py

```python
"""Shared orchestration data structures."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AgentTask:
    """A task to be executed by a Claude Code Agent."""
    agent_name: str
    prompt: str
    description: str
    workspace_path: str


@dataclass
class Action:
    """An action for the main Claude Code session to execute."""
    action_type: str  # "skill", "skills_parallel", "team", "bash", "gpu_poll", "experiment_wait", "done"
    agents: list[dict] | None = None
    skills: list[dict] | None = None
    team: dict | None = None
    bash_command: str | None = None
    gpu_poll: dict | None = None
    description: str = ""
    stage: str = ""
    iteration: int = 0
    estimated_minutes: int = 0
    checkpoint_info: dict | None = None
    experiment_monitor: dict | None = None
    execution_script: str = ""
```

**Step 2:** Write constants.py — mirror SibylSystem's pipeline stages

```python
"""Shared orchestration constants."""

RUNTIME_GITIGNORE_LINES = (
    "*.pyc", "__pycache__/", ".DS_Store", ".venv/",
    "CLAUDE.md", ".claude/agents", ".claude/skills",
    ".claude/settings.local.json", ".sibyl/system.json",
)

PAPER_SECTIONS = [
    ("intro", "Introduction"),
    ("related_work", "Related Work"),
    ("method", "Method"),
    ("experiments", "Experiments"),
    ("discussion", "Discussion"),
    ("conclusion", "Conclusion"),
]

CHECKPOINT_DIRS = {
    "idea_debate": "idea",
    "result_debate": "idea/result_debate",
    "writing_sections": "writing/sections",
    "writing_integrate": "writing/critique",
}

PIPELINE_STAGES = [
    "init",
    "literature_search",
    "idea_debate",
    "planning",
    "pilot_experiments",
    "idea_validation_decision",
    "experiment_cycle",
    "result_debate",
    "experiment_decision",
    "writing_outline",
    "writing_sections",
    "writing_integrate",
    "writing_final_review",
    "writing_latex",
    "review",
    "reflection",
    "quality_gate",
    "done",
]

SYNC_SKIP_STAGES = {
    "writing_outline", "writing_sections", "writing_integrate",
    "writing_final_review", "init", "quality_gate", "done", "lark_sync",
}
```

**Step 3:** Write tests

```python
# tests/test_models.py
from sibyl.orchestration.models import Action, AgentTask
from sibyl.orchestration.constants import PIPELINE_STAGES

def test_action_defaults():
    a = Action(action_type="skill", stage="init")
    assert a.agents is None
    assert a.execution_script == ""

def test_agent_task():
    t = AgentTask("lit", "search papers", "literature search", "/tmp/ws")
    assert t.agent_name == "lit"

def test_pipeline_stages_order():
    assert PIPELINE_STAGES[0] == "init"
    assert PIPELINE_STAGES[-1] == "done"
    assert len(PIPELINE_STAGES) == 18
```

Run: `pytest tests/test_models.py -v`

**Step 4:** Commit

```bash
git add sibyl/orchestration/models.py sibyl/orchestration/constants.py tests/test_models.py
git commit -m "feat: add core orchestration models and pipeline constants"
```

---

### Task 1.3: Configuration System

**Files:**
- Create: `sibyl/config.py`
- Create: `config.example.yaml`

**Step 1:** Write config.py — mirror SibylSystem Config dataclass but with RunPod-specific fields instead of SSH

```python
"""Configuration system with YAML loading and validation."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
import yaml


@dataclass
class AgentConfig:
    model: str = "claude-opus-4-6"
    max_tokens: int = 64000
    temperature: float = 0.7


@dataclass
class Config:
    workspaces_dir: Path = Path("workspaces")

    # Reserved agent configs (runtime routing is via .claude/agents + model_tiers)
    ideation: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.9))
    planning: AgentConfig = field(default_factory=AgentConfig)
    experiment: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.3))
    writing: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.5))

    max_parallel_tasks: int = 4
    idea_exp_cycles: int = 6
    idea_validation_rounds: int = 4
    max_iterations: int = 10
    max_iterations_cap: int = 100
    experiment_timeout: int = 300
    review_enabled: bool = True

    language: str = "en"

    # Compute backend: always RunPod
    compute_backend: str = "runpod"

    # RunPod configuration
    runpod_api_key: str = ""            # RUNPOD_API_KEY env var fallback
    runpod_gpu_type: str = "NVIDIA A100 80GB PCIe"
    runpod_gpu_count: int = 1
    runpod_image: str = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
    runpod_volume_id: str = ""          # persistent volume for datasets/checkpoints
    runpod_disk_gb: int = 50
    runpod_volume_mount: str = "/workspace"
    runpod_cloud_type: str = "COMMUNITY"  # "COMMUNITY" | "SECURE"
    runpod_template_id: str = ""        # optional: use existing template
    runpod_max_pods: int = 4            # max concurrent pods
    runpod_spot: bool = True            # use spot instances for cost savings
    runpod_env_setup_script: str = ""   # bash script to run on pod startup

    # GPU scheduling (within RunPod pods)
    max_gpus: int = 4
    gpus_per_task: int = 1

    # Pilot experiments
    pilot_samples: int = 100
    pilot_timeout: int = 900
    pilot_seeds: list[int] = field(default_factory=lambda: [42])

    # Full experiments
    full_seeds: list[int] = field(default_factory=lambda: [42, 123, 456])

    # Research focus (1=explore .. 5=deep_focus)
    research_focus: int = 3

    # Multi-agent debate
    debate_rounds: int = 2
    writing_revision_rounds: int = 2

    # Writing mode
    writing_mode: str = "parallel"
    speculative_outline: bool = True

    # Codex integration
    codex_enabled: bool = False
    codex_model: str = ""
    codex_idea_rounds: int = 2
    codex_writing_model: str = ""

    # Iteration directories
    iteration_dirs: bool = True

    # Lark sync
    lark_enabled: bool = False

    # Auto evolution
    evolution_enabled: bool = True

    # Self-healing
    self_heal_enabled: bool = True
    self_heal_interval_sec: int = 300
    self_heal_max_attempts: int = 3

    # Experiment supervisor
    supervisor_enabled: bool = False

    # Orchestra external skills
    orchestra_skills_enabled: bool = True
    orchestra_skills_dir: str = "~/.orchestra/skills"
    orchestra_skills_max: int = 15

    # Model routing
    model_tiers: dict = field(default_factory=lambda: {
        "heavy": "claude-opus-4-6",
        "standard": "claude-opus-4-6",
        "light": "claude-sonnet-4-6",
    })
    agent_tier_map: dict = field(default_factory=lambda: {
        "synthesizer": "heavy", "supervisor": "heavy",
        "supervisor_decision": "heavy", "editor": "heavy",
        "final_critic": "heavy", "critic": "heavy", "reflection": "heavy",
        "literature_researcher": "standard",
        "optimist": "light", "skeptic": "light", "strategist": "light",
        "section_critic": "light", "idea_critique": "light",
    })

    @staticmethod
    def _resolve_local_path(raw_value: str, base_dir: Path) -> Path:
        path = Path(raw_value).expanduser()
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        return path

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        config_path = Path(path).expanduser().resolve()
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        cfg = cls()
        raw_wd = str(data.get("workspaces_dir", cfg.workspaces_dir))
        cfg.workspaces_dir = cls._resolve_local_path(raw_wd, config_path.parent)
        for agent_name in ["ideation", "planning", "experiment", "writing"]:
            if agent_name in data:
                setattr(cfg, agent_name, AgentConfig(**data[agent_name]))
        # Simple scalar + list fields
        for key, val in data.items():
            if key in ("workspaces_dir", "ideation", "planning", "experiment", "writing"):
                continue
            if hasattr(cfg, key):
                if isinstance(getattr(cfg, key), dict) and isinstance(val, dict):
                    getattr(cfg, key).update(val)
                else:
                    setattr(cfg, key, val)
        # Env var fallback for API key
        if not cfg.runpod_api_key:
            import os
            cfg.runpod_api_key = os.environ.get("RUNPOD_API_KEY", "")
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        if self.compute_backend != "runpod":
            raise ValueError(f"Only 'runpod' compute_backend supported, got '{self.compute_backend}'")
        if self.language not in ("zh", "en"):
            raise ValueError(f"Invalid language '{self.language}'")
        if not 1 <= self.research_focus <= 5:
            raise ValueError(f"research_focus must be 1-5, got {self.research_focus}")
        if self.writing_mode not in ("sequential", "parallel", "codex"):
            raise ValueError(f"Invalid writing_mode '{self.writing_mode}'")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["workspaces_dir"] = str(self.workspaces_dir)
        return data

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False)
```

**Step 2:** Write config.example.yaml

```yaml
# DeepResearch (Tao Architecture) — Project Configuration

language: en

# RunPod compute (always RunPod)
compute_backend: runpod
runpod_gpu_type: "NVIDIA A100 80GB PCIe"
runpod_gpu_count: 1
runpod_image: "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
runpod_volume_id: ""
runpod_disk_gb: 50
runpod_max_pods: 4
runpod_spot: true

# GPU scheduling
max_gpus: 4
gpus_per_task: 1

# Research
research_focus: 3
idea_exp_cycles: 6
max_iterations: 10
pilot_samples: 100

# Writing
writing_mode: parallel
writing_revision_rounds: 2

# Features
evolution_enabled: true
self_heal_enabled: true
lark_enabled: false
```

**Step 3:** Write test

```python
# tests/test_config.py
import tempfile, os
from pathlib import Path
from sibyl.config import Config

def test_config_defaults():
    cfg = Config()
    assert cfg.compute_backend == "runpod"
    assert cfg.max_gpus == 4
    assert cfg.language == "en"

def test_config_from_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("language: zh\nresearch_focus: 5\nmax_gpus: 8\n")
        f.flush()
        cfg = Config.from_yaml(f.name)
    os.unlink(f.name)
    assert cfg.language == "zh"
    assert cfg.research_focus == 5
    assert cfg.max_gpus == 8

def test_config_validation():
    import pytest
    cfg = Config()
    cfg.compute_backend = "local"
    with pytest.raises(ValueError):
        cfg._validate()
```

Run: `pytest tests/test_config.py -v`

**Step 4:** Commit

```bash
git add sibyl/config.py config.example.yaml tests/test_config.py
git commit -m "feat: add config system with RunPod-only compute backend"
```

---

### Task 1.4: Paths & Exception Handling

**Files:**
- Create: `sibyl/_paths.py`
- Create: `sibyl/event_logger.py`
- Create: `sibyl/error_collector.py`

**Step 1:** Write _paths.py

```python
"""Central path resolution."""
from pathlib import Path
import os

def sibyl_root() -> Path:
    """Return the Tao system root (repo checkout)."""
    env = os.environ.get("SIBYL_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent

def system_data_dir() -> Path:
    """Return ~/.sibyl/ for cross-project data."""
    return Path.home() / ".sibyl"
```

**Step 2:** Write event_logger.py (structured JSONL logging)

```python
"""Structured event logging to JSONL files."""
from __future__ import annotations
import json, time
from pathlib import Path

def log_event(log_dir: str | Path, event_type: str, data: dict) -> None:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.time(), "type": event_type, **data}
    log_file = log_dir / "events.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

**Step 3:** Write error_collector.py

```python
"""Structured error collection for self-healing."""
from __future__ import annotations
import json, time
from pathlib import Path

def collect_error(log_dir: str | Path, category: str, message: str,
                  details: dict | None = None) -> None:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "category": category,
        "message": message,
        "details": details or {},
    }
    with open(log_dir / "errors.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

**Step 4:** Commit

```bash
git add sibyl/_paths.py sibyl/event_logger.py sibyl/error_collector.py
git commit -m "feat: add path resolution, event logger, error collector"
```

---

## Phase 2: Workspace Management

### Task 2.1: Workspace System

**Files:**
- Create: `sibyl/workspace.py`
- Create: `sibyl/orchestration/workspace_paths.py`
- Create: `tests/test_workspace.py`

Mirror SibylSystem's Workspace class — the filesystem communication hub for all agents. This creates and manages:

```
<project>/
├── status.json          # WorkspaceStatus
├── config.yaml
├── topic.txt
├── CLAUDE.md
├── idea/                # proposals, perspectives, debate
├── plan/                # task_plan.json, pilot_plan.json
├── exp/                 # code, results, gpu_progress.json
├── writing/             # outline, sections, critique, paper.md, latex/
├── reflection/          # lessons_learned.md, action_plan.json
├── context/             # literature.md
├── supervisor/
├── logs/
└── lark_sync/
```

**Key classes:**
- `WorkspaceStatus` dataclass (stage, iteration, errors, paused, stop_requested)
- `Workspace` class with methods: `read_file()`, `write_file()`, `get_status()`, `update_stage()`, `active_root`, `project_path()`, `active_path()`, `git_commit()`, `git_tag()`
- Iteration directory support (`iter_001/`, `iter_002/`, `current/` symlink)

Implementation: Port from `/tmp/AutoResearch-SibylSystem/sibyl/workspace.py` — adapt to RunPod paths.

**Step 1:** Write the workspace module (large file, ~800 lines)
**Step 2:** Write workspace_paths.py helper
**Step 3:** Write tests for workspace creation, status, file I/O, iteration dirs
**Step 4:** Commit

---

## Phase 3: State Machine & Orchestration

### Task 3.1: State Machine

**Files:**
- Create: `sibyl/orchestration/state_machine.py`
- Create: `tests/test_state_machine.py`

Mirror SibylSystem's state machine with all transition logic:
- `natural_next_stage()`: Computes next stage from current stage + result
- Pivot logic: `experiment_decision` PIVOT → loops to `idea_debate`
- Validation logic: `idea_validation_decision` REFINE/PIVOT → loops
- Writing revision: `writing_final_review` score < 7.0 → loops to `writing_integrate`
- Quality gate: score >= threshold AND iteration >= 2 → DONE
- `is_pipeline_done()`, `clear_iteration_artifacts()`, `reset_experiment_runtime_state()`

**Step 1:** Write state_machine.py
**Step 2:** Write tests covering all transition paths (forward, pivot, refine, quality gate)
**Step 3:** Commit

---

### Task 3.2: Lifecycle & Action Dispatcher

**Files:**
- Create: `sibyl/orchestration/lifecycle.py`
- Create: `sibyl/orchestration/action_dispatcher.py`

**lifecycle.py**: Generates Action objects for each pipeline stage:
- `get_next_action(workspace, config)` → Action
- `record_result(workspace, stage, result, score)`

**action_dispatcher.py**: Converts Action → deterministic execution script:
- `render_execution_script(action)` → str
- Script generators: `_script_skill()`, `_script_skills_parallel()`, `_script_team()`, `_script_bash()`, `_script_gpu_poll()`, `_script_experiment_wait()`

**Step 1:** Write lifecycle.py
**Step 2:** Write action_dispatcher.py
**Step 3:** Write tests
**Step 4:** Commit

---

### Task 3.3: Action Builders

**Files:**
- Create: `sibyl/orchestration/simple_actions.py`
- Create: `sibyl/orchestration/team_actions.py`
- Create: `sibyl/orchestration/experiment_actions.py`
- Create: `sibyl/orchestration/writing_artifacts.py`
- Create: `sibyl/orchestration/review_artifacts.py`

Each module builds stage-specific Action objects:
- **simple_actions**: Literature search, planning, quality gate
- **team_actions**: Idea debate (6 agents), result debate, writing critique
- **experiment_actions**: Pilot experiments, experiment cycle, GPU poll, experiment wait
- **writing_artifacts**: Writing outline/sections/integrate/final_review/latex
- **review_artifacts**: Review, reflection

**Step 1-5:** Write each module
**Step 6:** Write tests
**Step 7:** Commit

---

### Task 3.4: Orchestrator (Main Entry Point)

**Files:**
- Create: `sibyl/orchestrate.py`

The `FarsOrchestrator` class — the main API surface:
- `init_project(topic)` → creates workspace
- `get_next_action()` → Action (deterministic)
- `record_result(stage, result, score)` → advances state

Plus CLI-callable functions:
- `cli_next(workspace_path)` → JSON action
- `cli_record(workspace_path, stage, result, score)` → advances
- `cli_status(workspace_path)` → JSON status
- `cli_init(topic, config_path)` → workspace path
- `render_skill_prompt(workspace_path, skill_name)` → compiled prompt

**Step 1:** Write orchestrate.py
**Step 2:** Write tests
**Step 3:** Commit

---

## Phase 4: RunPod Compute Backend

### Task 4.1: Compute Base & RunPod Backend

**Files:**
- Create: `sibyl/compute/base.py`
- Create: `sibyl/compute/runpod_backend.py`
- Create: `sibyl/compute/__init__.py`
- Create: `tests/test_compute_backend.py`

**base.py**: Abstract ComputeBackend (same interface as SibylSystem):
- `backend_type` property
- `project_dir(ws_name)` → str
- `env_cmd(project_name)` → str
- `gpu_poll_script(...)` → str
- `experiment_monitor_script(...)` → str
- `from_config(config, workspace_active_root)` → ComputeBackend

**runpod_backend.py**: RunPod-specific implementation:
- Uses RunPod Python SDK (`runpod`) for pod lifecycle management
- `create_pod(config)` → pod_id (creates GPU pod)
- `terminate_pod(pod_id)` → None
- `list_pods()` → list of active pods
- `get_pod_ssh_info(pod_id)` → (host, port, key)
- `project_dir(ws_name)` → `/workspace/projects/{ws_name}` (inside pod)
- `env_cmd(project_name)` → conda/venv activation on pod
- `gpu_poll_script()` → bash script that runs nvidia-smi on RunPod pod
- `experiment_monitor_script()` → bash daemon monitoring experiments on pod
- `upload_code(pod_id, local_path, remote_path)` → rsync code to pod
- `download_results(pod_id, remote_path, local_path)` → rsync results back

```python
# sibyl/compute/runpod_backend.py
"""RunPod compute backend — create/manage GPU pods for experiments."""
from __future__ import annotations
import os, subprocess, json
from typing import TYPE_CHECKING
from sibyl.compute.base import ComputeBackend

if TYPE_CHECKING:
    from sibyl.config import Config


class RunPodBackend(ComputeBackend):
    """Execute experiments on RunPod GPU pods."""

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._api_key = config.runpod_api_key or os.environ.get("RUNPOD_API_KEY", "")

    @property
    def backend_type(self) -> str:
        return "runpod"

    def project_dir(self, ws_name: str) -> str:
        return f"{self._config.runpod_volume_mount}/projects/{ws_name}"

    def env_cmd(self, project_name: str) -> str:
        return f"cd {self.project_dir(project_name)} &&"

    def create_pod(self, name: str) -> dict:
        """Create a RunPod GPU pod. Returns pod info dict."""
        import runpod
        runpod.api_key = self._api_key
        pod = runpod.create_pod(
            name=name,
            image_name=self._config.runpod_image,
            gpu_type_id=self._config.runpod_gpu_type,
            gpu_count=self._config.runpod_gpu_count,
            volume_in_gb=self._config.runpod_disk_gb,
            volume_mount_path=self._config.runpod_volume_mount,
            cloud_type=self._config.runpod_cloud_type,
            network_volume_id=self._config.runpod_volume_id or None,
        )
        return pod

    def terminate_pod(self, pod_id: str) -> None:
        import runpod
        runpod.api_key = self._api_key
        runpod.terminate_pod(pod_id)

    def list_pods(self) -> list[dict]:
        import runpod
        runpod.api_key = self._api_key
        return runpod.get_pods()

    def gpu_poll_script(self, candidate_gpu_ids, threshold_mb, poll_interval_sec,
                        max_polls, marker_file, aggressive_mode, aggressive_threshold_pct) -> str:
        # RunPod pods have dedicated GPUs — always free
        # But we still poll to confirm pod is ready and GPUs are available
        return f"""#!/bin/bash
set -e
MARKER="{marker_file}"
THRESHOLD={threshold_mb}
INTERVAL={poll_interval_sec}
MAX_POLLS={max_polls}
poll=0
while true; do
    FREE_GPUS=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | \\
        awk -F', ' '$2 < '"$THRESHOLD"' {{print $1}}' | tr '\\n' ',' | sed 's/,$//')
    if [ -n "$FREE_GPUS" ]; then
        echo "[{{\\"gpu_ids\\": [$FREE_GPUS]}}]" > "$MARKER"
        exit 0
    fi
    poll=$((poll + 1))
    [ $MAX_POLLS -gt 0 ] && [ $poll -ge $MAX_POLLS ] && exit 1
    sleep $INTERVAL
done
"""

    def experiment_monitor_script(self, project_dir, task_ids, poll_interval_sec,
                                   timeout_minutes, marker_file, workspace_path,
                                   heartbeat_polls, task_gpu_map) -> str:
        task_ids_str = " ".join(task_ids)
        return f"""#!/bin/bash
set -e
PROJECT_DIR="{project_dir}"
MARKER="{marker_file}"
INTERVAL={poll_interval_sec}
TIMEOUT_SEC=$((60 * {timeout_minutes}))
TASK_IDS=({task_ids_str})
START=$(date +%s)
while true; do
    ALL_DONE=true
    for tid in "${{TASK_IDS[@]}}"; do
        if [ -f "$PROJECT_DIR/${{tid}}_DONE" ]; then
            continue
        fi
        ALL_DONE=false
        if [ -f "$PROJECT_DIR/${{tid}}.pid" ]; then
            PID=$(cat "$PROJECT_DIR/${{tid}}.pid")
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "DEAD:$tid" >> "$MARKER"
            fi
        fi
    done
    if $ALL_DONE; then
        echo "ALL_DONE" >> "$MARKER"
        exit 0
    fi
    NOW=$(date +%s)
    [ $((NOW - START)) -ge $TIMEOUT_SEC ] && echo "TIMEOUT" >> "$MARKER" && exit 1
    sleep $INTERVAL
done
"""

    @classmethod
    def from_config(cls, config: "Config", workspace_active_root: str = "") -> "RunPodBackend":
        return cls(config=config)
```

**Step 1:** Write base.py
**Step 2:** Write runpod_backend.py
**Step 3:** Write tests (mock RunPod API calls)
**Step 4:** Commit

---

## Phase 5: GPU Scheduler & Experiment Systems

### Task 5.1: GPU Scheduler

**Files:**
- Create: `sibyl/gpu_scheduler.py`
- Create: `tests/test_gpu_scheduler.py`

Port from SibylSystem — task parallelization engine:
- `get_next_batch(workspace_root, gpu_ids, mode, gpus_per_task)` → list of task assignments
- Topological sort on `depends_on` graph
- GPU progress tracking (`gpu_progress.json`)
- Global GPU leases (`~/.sibyl/system/scheduler/gpu_leases.json`)
- `gpu_poll_wait_script()` → bash script
- `experiment_monitor_script()` → bash daemon

Adapt for RunPod: pods have dedicated GPUs, so lease management is simpler (pod-level, not GPU-level).

**Step 1:** Write gpu_scheduler.py
**Step 2:** Write tests
**Step 3:** Commit

---

### Task 5.2: Experiment Recovery & Records

**Files:**
- Create: `sibyl/experiment_recovery.py`
- Create: `sibyl/experiment_records.py`
- Create: `sibyl/experiment_digest.py`

**experiment_recovery.py**: Crash detection & state restoration
- `ExperimentState` dataclass (schema_version, tasks, last_recovery_at, recovery_log)
- `generate_detection_script()` → bash script checking DONE/PID/DEAD status
- `sync_completed_from_progress()`, `register_dispatched_tasks()`

**experiment_records.py**: JSONL-based experiment DB
- `record_experiment()`, `load_experiments()`, `summary()`

**experiment_digest.py**: Human-readable experiment summaries

**Step 1-3:** Write each module
**Step 4:** Write tests
**Step 5:** Commit

---

## Phase 6: Prompt System

### Task 6.1: Prompt Templates

**Files:**
- Create: `sibyl/prompts/_common.md` — shared workspace conventions
- Create: `sibyl/prompts/_experiment_protocol.md` — remote experiment rules
- Create: `sibyl/prompts/innovator.md` — idea generation
- Create: `sibyl/prompts/pragmatist.md`
- Create: `sibyl/prompts/theoretical.md`
- Create: `sibyl/prompts/contrarian.md`
- Create: `sibyl/prompts/interdisciplinary.md`
- Create: `sibyl/prompts/empiricist.md`
- Create: `sibyl/prompts/synthesizer.md`
- Create: `sibyl/prompts/literature_researcher.md`
- Create: `sibyl/prompts/planner.md`
- Create: `sibyl/prompts/experimenter.md`
- Create: `sibyl/prompts/experiment_supervisor.md`
- Create: `sibyl/prompts/supervisor.md`
- Create: `sibyl/prompts/supervisor_decision.md`
- Create: `sibyl/prompts/idea_validation_decision.md`
- Create: `sibyl/prompts/outline_writer.md`
- Create: `sibyl/prompts/section_writer.md`
- Create: `sibyl/prompts/sequential_writer.md`
- Create: `sibyl/prompts/editor.md`
- Create: `sibyl/prompts/latex_writer.md`
- Create: `sibyl/prompts/final_critic.md`
- Create: `sibyl/prompts/section_critic.md`
- Create: `sibyl/prompts/critic.md`
- Create: `sibyl/prompts/reflection.md`
- Create: `sibyl/prompts/self_healer.md`
- Create: `sibyl/prompts/result_synthesizer.md`
- Create: `sibyl/prompts/novelty_checker.md`
- Create: `sibyl/prompts/simulated_reviewer.md`

Port prompt templates from SibylSystem, adapting for:
- RunPod-specific experiment execution context
- Our project conventions

**Step 1:** Copy and adapt _common.md with workspace conventions
**Step 2:** Copy and adapt _experiment_protocol.md for RunPod
**Step 3-N:** Copy and adapt each agent prompt
**Step N+1:** Commit

---

### Task 6.2: Prompt Loader

**Files:**
- Create: `sibyl/orchestration/prompt_loader.py`
- Create: `sibyl/orchestration/context_builder.py`
- Create: `sibyl/orchestra_skills.py`

**prompt_loader.py**: Dynamic prompt compilation:
1. Load base role prompt from `sibyl/prompts/{agent_name}.md`
2. Append runtime sections (locale/workspace/evidence contracts)
3. Inject experiment protocol (for experimenter agents)
4. Inject paper output contract (for writing agents)
5. Load project memory + evolution overlays
6. Inject orchestra skills index

**context_builder.py**: Priority-based context packing for token limits.

**orchestra_skills.py**: Scans external skills dir, builds index for agent prompts.

**Step 1-3:** Write each module
**Step 4:** Write tests
**Step 5:** Commit

---

## Phase 7: Self-Healing & Evolution

### Task 7.1: Auto-Fix & Self-Healing

**Files:**
- Create: `sibyl/auto_fix.py`
- Create: `sibyl/self_heal.py`
- Create: `tests/test_self_heal.py`

**auto_fix.py**: Mechanical fixes (no LLM cost):
- `_fix_import()`: pip install missing modules
- `_fix_missing_dir()`: mkdir -p
- `_fix_config()`: YAML/JSON syntax repair

**self_heal.py**: Error routing + circuit breaker:
- `SelfHealRouter` class
- Error categories → repair skill pipelines
- Track fix attempts, circuit breaker (max 3 per error)
- Deduplication + prioritization

**Step 1-2:** Write modules
**Step 3:** Write tests
**Step 4:** Commit

---

### Task 7.2: Reflection & Evolution

**Files:**
- Create: `sibyl/reflection.py`
- Create: `sibyl/evolution.py`
- Create: `sibyl/orchestration/reflection_postprocess.py`
- Create: `tests/test_evolution.py`

**reflection.py**: Iteration logging + reflection agent support.

**evolution.py**: Cross-project self-improvement:
- `IssueCategory` enum (8 categories: SYSTEM, EXPERIMENT, WRITING, ANALYSIS, PLANNING, PIPELINE, IDEATION, EFFICIENCY)
- Issue normalization and deduplication
- Time-decay learning (`_compute_effectiveness()`)
- Agent-specific lessons overlays generation
- `evolution_log.jsonl` tracking

**reflection_postprocess.py**: Post-reflection hook:
- `run_post_reflection_hook()`: Extract issues, normalize, generate overlays

**Step 1-3:** Write modules
**Step 4:** Write tests
**Step 5:** Commit

---

## Phase 8: Plugin System

### Task 8.1: Plugin Commands

**Files:**
- Create: `plugin/.claude-plugin/manifest.json`
- Create: `plugin/commands/init.md`
- Create: `plugin/commands/start.md`
- Create: `plugin/commands/continue.md`
- Create: `plugin/commands/resume.md`
- Create: `plugin/commands/stop.md`
- Create: `plugin/commands/status.md`
- Create: `plugin/commands/pivot.md`
- Create: `plugin/commands/evolve.md`
- Create: `plugin/commands/debug.md`
- Create: `plugin/commands/rebuttal-init.md`
- Create: `plugin/commands/rebuttal-start.md`
- Create: `plugin/commands/rebuttal-status.md`
- Create: `plugin/commands/_orchestration-loop.md`

Mirror SibylSystem's plugin commands — each is a markdown-based Claude Code skill:
- `/deepresearch:start spec.md` — launch new project
- `/deepresearch:continue .` — resume workspace
- `/deepresearch:resume` — re-enter autonomous loop
- `/deepresearch:init` — initialize first workspace
- `/deepresearch:status` — show status
- `/deepresearch:stop` — pause project
- `/deepresearch:pivot` — force idea pivot
- `/deepresearch:evolve` — trigger evolution

**Step 1:** Write manifest.json
**Step 2-N:** Write each command .md
**Step N+1:** Commit

---

### Task 8.2: Plugin Hooks

**Files:**
- Create: `plugin/hooks/scripts/on-bash-complete.sh`
- Create: `plugin/hooks/scripts/on-session-start.sh`
- Create: `plugin/hooks/scripts/on-stop.sh`

Lifecycle hooks for automatic daemon management:
- `on-bash-complete`: Detect sync_requested → launch background sync
- `on-session-start`: Restore pending work, restart dead daemons
- `on-stop`: Clean up PID files

**Step 1-3:** Write each script
**Step 4:** Commit

---

## Phase 9: Runtime Assets & LaTeX

### Task 9.1: Runtime Assets

**Files:**
- Create: `sibyl/runtime_assets.py`
- Create: `sibyl/latex_pipeline.py`
- Create: `sibyl/lark_sync.py`
- Create: `sibyl/lark_markdown_converter.py`

**runtime_assets.py**: Manage `.claude/agents`, `.claude/skills`, `.claude/settings.json`, `.sibyl/project/` overlays, and generated `CLAUDE.md`.

**latex_pipeline.py**: Markdown → LaTeX conversion + PDF compilation (NeurIPS format).

**lark_sync.py**: Feishu/Lark document sync (optional feature).

**lark_markdown_converter.py**: Deterministic markdown → Feishu blocks converter.

**Step 1-4:** Write each module
**Step 5:** Commit

---

## Phase 10: CLI

### Task 10.1: Main CLI

**Files:**
- Create: `sibyl/cli.py`
- Create: `sibyl/orchestration/cli_core.py`
- Create: `sibyl/orchestration/project_cli.py`
- Create: `sibyl/orchestration/runtime_cli.py`
- Create: `sibyl/orchestration/ops_cli.py`

**cli.py**: Typer-based CLI with commands:
- `status [project]` — show dashboard
- `evolve [--apply] [--reset]` — evolution management
- `experiment-status <workspace>` — check running experiments
- `dispatch <workspace>` — dynamic task dispatch
- `self-heal-scan [workspace]` — scan for fixable errors
- `dashboard [workspace]` — JSON dashboard data

**cli_core.py**: Core CLI helpers shared across sub-CLIs.

**Step 1-4:** Write each module
**Step 5:** Write tests
**Step 6:** Commit

---

## Phase 11: WebUI & Dashboard

### Task 11.1: Dashboard Server

**Files:**
- Create: `sibyl/dashboard/__init__.py`
- Create: `sibyl/dashboard/server.py`
- Create: `sibyl/orchestration/dashboard_data.py`

**dashboard_data.py**: Generate JSON dashboard data (stage, iteration, agent status, GPU utilization, cost).

**server.py**: Simple Flask server serving dashboard data.

**Step 1-2:** Write modules
**Step 3:** Commit

---

### Task 11.2: WebUI Backend

**Files:**
- Create: `sibyl/webui/app.py`
- Create: `sibyl/webui/control_api.py`
- Create: `sibyl/webui/monitor_api.py`
- Create: `sibyl/webui/session_registry.py`
- Create: `sibyl/webui/state_watcher.py`
- Create: `sibyl/webui/conversation_watcher.py`
- Create: `sibyl/webui/message_injector.py`
- Create: `sibyl/webui/ws_hub.py`

Mirror SibylSystem's WebUI backend:
- Flask + WebSocket for real-time monitoring
- Project state transitions via control API
- Experiment status via monitor API
- File system watching for artifact changes
- Session management

**Step 1-8:** Write each module
**Step 9:** Write tests
**Step 10:** Commit

---

## Phase 12: Rebuttal Pipeline

### Task 12.1: Rebuttal System

**Files:**
- Create: `sibyl/rebuttal/orchestrator.py`
- Create: `sibyl/rebuttal/actions.py`
- Create: `sibyl/rebuttal/cli.py`
- Create: `sibyl/rebuttal/config.py`
- Create: `sibyl/rebuttal/constants.py`
- Create: `sibyl/rebuttal/prompt_helpers.py`
- Create: `sibyl/rebuttal/scoring.py`
- Create: `sibyl/rebuttal/state_machine.py`
- Create: `sibyl/rebuttal/workspace_setup.py`
- Create rebuttal prompt templates in `sibyl/prompts/rebuttal_*.md`

Independent state machine for adversarial peer review response:
- Stages: parse_reviews → strategy → rebuttal_draft → simulated_review → score_evaluate → final_synthesis
- Round-based iteration with score-based stopping
- Simulated reviewer feedback drives refinement

**Step 1-9:** Write each module
**Step 10:** Write prompt templates
**Step 11:** Write tests
**Step 12:** Commit

---

## Phase 13: Agent & Skill Definitions

### Task 13.1: Claude Code Agent Definitions

**Files:**
- Create: `.claude/agents/` directory with agent YAML files

Define 20+ specialized agents with model tier assignments:
- **Heavy tier** (Opus): synthesizer, supervisor, editor, critic, reflection
- **Standard tier** (Opus): literature, planner, experimenter, idea agents, writing agents
- **Light tier** (Sonnet): critics, comparative agents

Each agent YAML specifies: name, model, description, system prompt reference.

**Step 1:** Create agent definitions
**Step 2:** Commit

---

### Task 13.2: Claude Code Skill Definitions

**Files:**
- Create: `.claude/skills/` directory with skill markdown files

Define 40+ specialized skills as `context: fork` subagents:
- Literature & Ideas: tao-literature, tao-innovator, tao-pragmatist, etc.
- Planning & Experiments: tao-planner, tao-experimenter
- Writing: tao-outline-writer, tao-section-writer, tao-editor, etc.
- Analysis: tao-critic, tao-reflection
- Rebuttal: tao-rebuttal-strategist, tao-rebuttal-writer, etc.

Each skill contains the dynamically-loaded prompt via shebang call to `render_skill_prompt()`.

**Step 1:** Create skill definitions
**Step 2:** Commit

---

## Phase 14: Integration & Testing

### Task 14.1: Demo & Smoke Test

**Files:**
- Create: `sibyl/demo.py`
- Create: `scripts/scaffold_demo.py`

**demo.py**: End-to-end smoke test scaffold:
- Creates a test workspace
- Runs through pipeline stages with mock data
- Validates workspace structure and state transitions

**Step 1:** Write demo.py
**Step 2:** Write scaffold script
**Step 3:** Commit

---

### Task 14.2: Comprehensive Test Suite

**Files:**
- Create: `tests/test_orchestrate.py`
- Create: `tests/test_state_machine.py` (if not already)
- Create: `tests/test_action_dispatcher.py`
- Create: `tests/test_gpu_scheduler.py`
- Create: `tests/test_workspace.py`
- Create: `tests/test_experiment_recovery.py`
- Create: `tests/test_self_heal.py`
- Create: `tests/test_evolution.py`
- Create: `tests/test_latex_pipeline.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_webui_app.py`
- Create: `tests/test_rebuttal.py`
- Create: `tests/conftest.py`

**Step 1:** Write conftest.py with shared fixtures
**Step 2-N:** Write each test file
**Step N+1:** Run full test suite: `pytest tests/ -v`
**Step N+2:** Commit

---

### Task 14.3: Update CLAUDE.md & README

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Create: `docs/setup-guide.md`

Update project documentation to reflect the new architecture:
- New package structure (`sibyl/` instead of `src/deepresearch/`)
- RunPod-only compute backend
- Plugin/skill usage
- CLI commands
- Setup guide for Claude Code + RunPod configuration

**Step 1:** Update CLAUDE.md
**Step 2:** Rewrite README.md
**Step 3:** Write setup-guide.md
**Step 4:** Commit

---

### Task 14.4: Final Verification

**Step 1:** Install package: `pip install -e ".[dev]"`
**Step 2:** Run full test suite: `pytest tests/ -v`
**Step 3:** Run type check: `mypy sibyl/`
**Step 4:** Run lint: `ruff check sibyl/`
**Step 5:** Verify CLI: `sibyl --help`
**Step 6:** Dry-run demo: `python -m sibyl.demo`
**Step 7:** Commit any fixes

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1.1-1.4 | Foundation: restructure, models, config, paths |
| 2 | 2.1 | Workspace management system |
| 3 | 3.1-3.4 | State machine, lifecycle, action dispatch, orchestrator |
| 4 | 4.1 | RunPod compute backend |
| 5 | 5.1-5.2 | GPU scheduler, experiment recovery |
| 6 | 6.1-6.2 | Prompt templates + loader |
| 7 | 7.1-7.2 | Self-healing + evolution |
| 8 | 8.1-8.2 | Plugin commands + hooks |
| 9 | 9.1 | Runtime assets, LaTeX, Lark |
| 10 | 10.1 | CLI |
| 11 | 11.1-11.2 | WebUI & dashboard |
| 12 | 12.1 | Rebuttal pipeline |
| 13 | 13.1-13.2 | Agent & skill definitions |
| 14 | 14.1-14.4 | Integration tests, docs, verification |

**Total: ~35 tasks across 14 phases.**

Old code is preserved on the `python` branch for reference.
