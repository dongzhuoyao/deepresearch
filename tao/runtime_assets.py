"""Runtime asset management for Claude Code integration."""
from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.config import Config


def setup_workspace_assets(workspace_root: str | Path, config: "Config") -> None:
    """Set up .claude/ directory and generated CLAUDE.md in workspace."""
    root = Path(workspace_root)

    # Create .claude directory structure
    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create .tao/project structure
    tao_dir = root / ".tao" / "project"
    tao_dir.mkdir(parents=True, exist_ok=True)
    (tao_dir / "overlays").mkdir(exist_ok=True)

    # Generate CLAUDE.md
    claude_md = _generate_claude_md(root, config)
    (root / "CLAUDE.md").write_text(claude_md, encoding="utf-8")


def _generate_claude_md(workspace_root: Path, config: "Config") -> str:
    """Generate CLAUDE.md with effective system instructions."""
    topic_file = workspace_root / "topic.txt"
    topic = topic_file.read_text(encoding="utf-8").strip() if topic_file.exists() else "Research Project"

    return f"""# Tao Research System — Workspace Instructions

## Research Topic
{topic}

## Workspace Structure
- `idea/` — Proposals, perspectives, debate records
- `plan/` — Task plans, methodology
- `exp/` — Experiment code, results, GPU progress
- `writing/` — Paper sections, critique, LaTeX
- `reflection/` — Lessons learned, action plans
- `context/` — Literature survey
- `logs/` — Event logs, iteration history

## Conventions
- JSON for structured data, Markdown for prose
- Paper content always in English
- Evidence required for all claims
- Log actions to `logs/research_diary.md`

## Compute
- All experiments run on RunPod GPU pods
- GPU type: {config.runpod_gpu_type}
- Max pods: {config.runpod_max_pods}

## Pipeline
- 18-stage autonomous pipeline with quality gates
- Iteration limit: {config.max_iterations}
- Writing mode: {config.writing_mode}
"""


def update_gitignore(workspace_root: str | Path) -> None:
    """Add runtime entries to .gitignore."""
    from tao.orchestration.constants import RUNTIME_GITIGNORE_LINES
    root = Path(workspace_root)
    gitignore = root / ".gitignore"

    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text().splitlines())

    new_lines = [line for line in RUNTIME_GITIGNORE_LINES if line not in existing]
    if new_lines:
        with open(gitignore, "a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(f"\n{line}")
