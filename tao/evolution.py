"""Cross-project self-evolution -- learn from research to improve prompts."""
from __future__ import annotations
import json
import math
import time
from enum import Enum
from pathlib import Path
from typing import Any


class IssueCategory(str, Enum):
    """Issue categories for classification."""
    SYSTEM = "system"
    EXPERIMENT = "experiment"
    WRITING = "writing"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    PIPELINE = "pipeline"
    IDEATION = "ideation"
    EFFICIENCY = "efficiency"


# Category synonyms for normalization
CATEGORY_SYNONYMS = {
    "ssh": IssueCategory.SYSTEM,
    "timeout": IssueCategory.SYSTEM,
    "oom": IssueCategory.SYSTEM,
    "gpu": IssueCategory.SYSTEM,
    "format": IssueCategory.SYSTEM,
    "method": IssueCategory.EXPERIMENT,
    "baseline": IssueCategory.EXPERIMENT,
    "reproducibility": IssueCategory.EXPERIMENT,
    "paper": IssueCategory.WRITING,
    "clarity": IssueCategory.WRITING,
    "structure": IssueCategory.WRITING,
    "stats": IssueCategory.ANALYSIS,
    "comparison": IssueCategory.ANALYSIS,
    "scope": IssueCategory.PLANNING,
    "resource": IssueCategory.PLANNING,
    "novelty": IssueCategory.IDEATION,
    "waste": IssueCategory.EFFICIENCY,
    "idle": IssueCategory.EFFICIENCY,
}


def normalize_issue_entry(raw: dict) -> dict:
    """Normalize an issue entry for deduplication and classification."""
    category = raw.get("category", "").lower()
    description = raw.get("description", raw.get("message", ""))
    severity = raw.get("severity", "medium")

    # Try to classify via synonyms
    resolved_category = None
    for synonym, cat in CATEGORY_SYNONYMS.items():
        if synonym in category or synonym in description.lower():
            resolved_category = cat.value
            break

    if resolved_category is None:
        # Try direct match
        try:
            resolved_category = IssueCategory(category).value
        except ValueError:
            resolved_category = IssueCategory.SYSTEM.value

    # Generate dedup key
    issue_key = f"{resolved_category}:{description[:80].lower().strip()}"

    return {
        "description": description,
        "category": resolved_category,
        "severity": severity,
        "status": raw.get("status", "open"),
        "issue_key": issue_key,
        "suggestion": raw.get("suggestion", ""),
    }


def compute_effectiveness(
    fix_history: list[dict],
    decay_rate: float = 0.1,
) -> float:
    """Compute fix effectiveness with exponential time decay.

    Each fix entry has {ts, success: bool}.
    More recent fixes are weighted more heavily.
    """
    if not fix_history:
        return 0.0

    now = time.time()
    weighted_successes = 0.0
    total_weight = 0.0

    for entry in fix_history:
        age_hours = (now - entry.get("ts", now)) / 3600
        weight = math.exp(-decay_rate * age_hours)
        total_weight += weight
        if entry.get("success", False):
            weighted_successes += weight

    if total_weight == 0:
        return 0.0
    return weighted_successes / total_weight


def generate_agent_overlay(
    agent_name: str,
    lessons: list[dict],
    max_lessons: int = 10,
) -> str:
    """Generate an agent-specific lessons overlay markdown.

    Injected into agent prompts to improve performance based on past issues.
    """
    if not lessons:
        return ""

    # Filter lessons relevant to this agent
    relevant = [l for l in lessons if _is_relevant(agent_name, l)]

    # Sort by recency (newer first)
    relevant.sort(key=lambda l: l.get("ts", 0), reverse=True)
    relevant = relevant[:max_lessons]

    if not relevant:
        return ""

    lines = [f"## Lessons Learned (auto-injected for {agent_name})\n"]
    for i, lesson in enumerate(relevant, 1):
        desc = lesson.get("description", "")
        suggestion = lesson.get("suggestion", "")
        lines.append(f"{i}. **{desc}**")
        if suggestion:
            lines.append(f"   - Fix: {suggestion}")

    return "\n".join(lines)


def log_evolution_event(
    workspace_root: str | Path,
    issues: list[dict],
    fixes: list[dict],
    quality_trajectory: str,
) -> None:
    """Log an evolution event to evolution_log.jsonl."""
    log_file = Path(workspace_root) / "logs" / "evolution_log.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "issues_count": len(issues),
        "fixes_count": len(fixes),
        "quality_trajectory": quality_trajectory,
        "categories": _count_categories(issues),
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_evolution_log(workspace_root: str | Path) -> list[dict]:
    """Load the evolution log."""
    log_file = Path(workspace_root) / "logs" / "evolution_log.jsonl"
    if not log_file.exists():
        return []
    entries = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _is_relevant(agent_name: str, lesson: dict) -> bool:
    """Check if a lesson is relevant to a specific agent."""
    category = lesson.get("category", "")
    # Map categories to relevant agents
    agent_categories = {
        "experimenter": ["experiment", "system", "efficiency"],
        "planner": ["planning", "experiment", "efficiency"],
        "writer": ["writing", "analysis"],
        "section_writer": ["writing"],
        "editor": ["writing"],
        "critic": ["writing", "analysis"],
        "supervisor": ["planning", "experiment", "writing"],
        "reflection": ["pipeline", "efficiency"],
        "innovator": ["ideation"],
        "literature": ["ideation", "analysis"],
    }

    relevant_cats = agent_categories.get(agent_name, list(IssueCategory))
    return category in relevant_cats


def _count_categories(issues: list[dict]) -> dict[str, int]:
    """Count issues by category."""
    counts: dict[str, int] = {}
    for issue in issues:
        cat = issue.get("category", "unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts
