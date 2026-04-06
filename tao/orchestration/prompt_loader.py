"""Dynamic prompt compilation — assembles agent prompts from templates + context."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from tao._paths import prompts_dir

if TYPE_CHECKING:
    from tao.config import Config
    from tao.workspace import Workspace


def load_prompt(agent_name: str) -> str:
    """Load a base prompt template by agent name."""
    prompt_file = prompts_dir() / f"{agent_name}.md"
    if not prompt_file.exists():
        return f"You are {agent_name}. Follow workspace conventions."
    return prompt_file.read_text(encoding="utf-8")


def load_shared_prompt(name: str) -> str:
    """Load a shared prompt section (e.g. _common, _experiment_protocol)."""
    prompt_file = prompts_dir() / f"{name}.md"
    if not prompt_file.exists():
        return ""
    return prompt_file.read_text(encoding="utf-8")


def compile_prompt(
    agent_name: str,
    workspace: "Workspace",
    config: "Config",
    extra_context: str = "",
) -> str:
    """Compile a full agent prompt with all context layers.

    Assembly order:
    1. Base role prompt
    2. Shared _common section
    3. Experiment protocol (if agent is experimenter/planner)
    4. Project memory
    5. Evolution overlay (agent-specific lessons)
    6. Research focus directive
    7. Extra context
    """
    sections = []

    # 1. Base role prompt
    base = load_prompt(agent_name)
    sections.append(base)

    # 2. Shared conventions
    common = load_shared_prompt("_common")
    if common:
        sections.append(f"\n---\n\n{common}")

    # 3. Experiment protocol (for relevant agents)
    experiment_agents = {"experimenter", "planner", "experiment_supervisor", "server_experimenter"}
    if agent_name in experiment_agents:
        protocol = load_shared_prompt("_experiment_protocol")
        if protocol:
            sections.append(f"\n---\n\n{protocol}")

    # 4. Project context
    topic = workspace.read_file("topic.txt") or ""
    if topic:
        sections.append(f"\n---\n\n## Research Topic\n\n{topic}")

    # 5. Project memory
    memory = workspace.read_file(".tao/project/memory.md")
    if memory:
        sections.append(f"\n---\n\n## Project Memory\n\n{memory}")

    # 6. Evolution overlay
    overlay_path = f".tao/project/overlays/{agent_name}.md"
    overlay = workspace.read_file(overlay_path)
    if overlay:
        sections.append(f"\n---\n\n{overlay}")

    # 7. Research focus directive
    focus = _research_focus_directive(config.research_focus)
    if focus:
        sections.append(f"\n---\n\n## Research Focus\n\n{focus}")

    # 8. Extra context
    if extra_context:
        sections.append(f"\n---\n\n{extra_context}")

    return "\n".join(sections)


def compile_team_prompt(
    team_name: str,
    agents: list[dict],
    workspace: "Workspace",
    config: "Config",
) -> str:
    """Compile a team-level prompt with teammate awareness."""
    lines = [f"# Team: {team_name}\n"]
    lines.append("## Your Teammates\n")
    for agent in agents:
        name = agent.get("name", "unknown")
        desc = agent.get("description", "")
        lines.append(f"- **{name}**: {desc}")
    lines.append("")
    lines.append("## Team Protocol")
    lines.append("- Each teammate writes their perspective independently")
    lines.append("- Read all perspectives before synthesizing")
    lines.append("- Cite specific teammate insights when building on their work")
    lines.append("- Disagree constructively with evidence")
    return "\n".join(lines)


def _research_focus_directive(focus: int) -> str:
    """Generate research focus directive based on config."""
    directives = {
        1: "**Explore Mode**: Cast a wide net. Maintain 3-4 candidate ideas. Pivot early and often if initial results are underwhelming.",
        2: "**Open Mode**: Lean toward exploring alternatives. Maintain 2-3 candidates. Consider pivoting when results fall below expectations.",
        3: "**Balanced Mode**: Default behavior. Weigh evidence before deciding to pivot or persist. Trust experiment results.",
        4: "**Focused Mode**: Persist with the current direction unless results clearly disprove the hypothesis. Maintain 1-2 candidates.",
        5: "**Deep Focus Mode**: Exhaust all optimization avenues before considering a pivot. Iterate on the current idea extensively.",
    }
    return directives.get(focus, directives[3])
