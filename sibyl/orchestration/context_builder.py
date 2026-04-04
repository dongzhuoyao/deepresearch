"""Priority-based context packing for agent prompts."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sibyl.workspace import Workspace


def build_context(
    workspace: "Workspace",
    sections: list[dict],
    max_chars: int = 100_000,
) -> str:
    """Build context string from prioritized sections.

    Each section: {"label": str, "content": str, "priority": int}
    Priority 1 = highest (always included), higher numbers = lower priority.
    Sections are added in priority order until max_chars is reached.
    """
    sorted_sections = sorted(sections, key=lambda s: s.get("priority", 99))

    result = []
    total = 0

    for section in sorted_sections:
        content = section.get("content", "")
        label = section.get("label", "")
        if not content:
            continue

        formatted = f"## {label}\n\n{content}\n" if label else content
        section_len = len(formatted)

        if total + section_len > max_chars:
            # Try to fit a truncated version
            remaining = max_chars - total - 50  # leave room for truncation note
            if remaining > 200:  # only truncate if meaningful content fits
                formatted = formatted[:remaining] + "\n\n[... truncated for context limit]"
                result.append(formatted)
                total += len(formatted)
            break

        result.append(formatted)
        total += section_len

    return "\n".join(result)


def gather_workspace_context(workspace: "Workspace") -> list[dict]:
    """Gather standard workspace context sections."""
    sections = []

    # High priority: topic and current status
    topic = workspace.read_file("topic.txt")
    if topic:
        sections.append({"label": "Research Topic", "content": topic, "priority": 1})

    # Medium priority: idea proposal
    proposal = workspace.read_file("idea/proposal.md")
    if proposal:
        sections.append({"label": "Current Proposal", "content": proposal, "priority": 2})

    # Medium priority: experiment plan
    plan = workspace.read_file("plan/methodology.md")
    if plan:
        sections.append({"label": "Methodology", "content": plan, "priority": 3})

    # Medium priority: results summary
    results = workspace.read_file("exp/results/summary.md")
    if results:
        sections.append({"label": "Results Summary", "content": results, "priority": 3})

    # Lower priority: literature context
    literature = workspace.read_file("context/literature.md")
    if literature:
        sections.append({"label": "Literature Context", "content": literature, "priority": 5})

    # Lower priority: reflection lessons
    lessons = workspace.read_file("reflection/lessons_learned.md")
    if lessons:
        sections.append({"label": "Lessons Learned", "content": lessons, "priority": 6})

    return sections
