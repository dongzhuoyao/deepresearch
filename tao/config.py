"""Configuration system with YAML loading and validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
import os
import yaml


@dataclass
class AgentConfig:
    """Per-phase model config (backward compat)."""
    model: str = "claude-opus-4-6"
    max_tokens: int = 64000
    temperature: float = 0.7


@dataclass
class Config:
    workspaces_dir: Path = Path("workspaces")

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

    # Compute — always RunPod
    compute_backend: str = "runpod"

    # RunPod configuration
    runpod_api_key: str = ""
    runpod_gpu_type: str = "NVIDIA A100 80GB PCIe"
    runpod_gpu_count: int = 1
    runpod_image: str = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
    runpod_volume_id: str = ""
    runpod_disk_gb: int = 50
    runpod_volume_mount: str = "/workspace"
    runpod_cloud_type: str = "COMMUNITY"
    runpod_template_id: str = ""
    runpod_max_pods: int = 4
    runpod_spot: bool = True
    runpod_env_setup_script: str = ""

    # GPU scheduling
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

    # Writing
    writing_mode: str = "parallel"
    speculative_outline: bool = True

    # Codex
    codex_enabled: bool = False
    codex_model: str = ""
    codex_idea_rounds: int = 2
    codex_writing_model: str = ""

    # Experiment mode
    experiment_mode: str = "runpod"

    # Iteration directories
    iteration_dirs: bool = True

    # Lark sync
    lark_enabled: bool = False

    # Evolution
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
        return cls._from_data(data, base_dir=config_path.parent)

    @classmethod
    def from_yaml_chain(cls, *paths: str) -> "Config":
        merged: dict = {}
        last_base: Path = Path.cwd()
        for path in paths:
            config_path = Path(path).expanduser().resolve()
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for key, val in data.items():
                if isinstance(val, dict) and isinstance(merged.get(key), dict):
                    merged[key].update(val)
                else:
                    merged[key] = val
            last_base = config_path.parent
        return cls._from_data(merged, base_dir=last_base)

    @classmethod
    def _from_data(cls, data: dict, *, base_dir: Path) -> "Config":
        cfg = cls()
        # Resolve workspaces_dir
        raw_wd = str(data.get("workspaces_dir", cfg.workspaces_dir))
        cfg.workspaces_dir = cls._resolve_local_path(raw_wd, base_dir)
        # Agent configs
        for agent_name in ["ideation", "planning", "experiment", "writing"]:
            if agent_name in data:
                setattr(cfg, agent_name, AgentConfig(**data[agent_name]))
        # All other fields
        skip = {"workspaces_dir", "ideation", "planning", "experiment", "writing"}
        for key, val in data.items():
            if key in skip:
                continue
            if hasattr(cfg, key):
                if isinstance(getattr(cfg, key), dict) and isinstance(val, dict):
                    getattr(cfg, key).update(val)
                else:
                    setattr(cfg, key, val)
        # Env var fallback
        if not cfg.runpod_api_key:
            cfg.runpod_api_key = os.environ.get("RUNPOD_API_KEY", "")
        # Resolve orchestra_skills_dir
        if "orchestra_skills_dir" in data:
            cfg.orchestra_skills_dir = str(
                cls._resolve_local_path(str(data["orchestra_skills_dir"]), base_dir)
            )
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        if self.compute_backend != "runpod":
            raise ValueError(f"Only 'runpod' compute_backend supported, got '{self.compute_backend}'")
        if self.language not in ("zh", "en"):
            raise ValueError(f"Invalid language '{self.language}', must be 'zh' or 'en'")
        if isinstance(self.research_focus, bool) or not isinstance(self.research_focus, int) or not 1 <= self.research_focus <= 5:
            raise ValueError(f"research_focus must be 1-5, got {self.research_focus}")
        if self.writing_mode not in ("sequential", "parallel", "codex"):
            raise ValueError(f"Invalid writing_mode '{self.writing_mode}'")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["workspaces_dir"] = str(self.workspaces_dir)
        return data

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False)
