"""Post-reflection hook -- triggers evolution after each iteration."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from tao.reflection import log_iteration, get_quality_trajectory, assess_trajectory
from tao.evolution import normalize_issue_entry, log_evolution_event, generate_agent_overlay


def run_post_reflection_hook(
    workspace_root: str | Path,
    iteration: int,
    action_plan: dict | None = None,
    supervisor_issues: list[dict] | None = None,
    quality_score: float = 0.0,
) -> dict:
    """Run post-reflection processing.

    1. Extract issues from supervisor review + action plan
    2. Normalize and classify issues
    3. Compute quality trajectory
    4. Log iteration and evolution events
    5. Generate agent overlays

    Returns summary dict.
    """
    workspace_root = Path(workspace_root)

    # Collect all issues
    raw_issues = []
    if supervisor_issues:
        raw_issues.extend(supervisor_issues)
    if action_plan:
        raw_issues.extend(action_plan.get("issues", []))

    # Normalize
    normalized = [normalize_issue_entry(issue) for issue in raw_issues]

    # Dedup by issue_key
    seen_keys: set[str] = set()
    deduped: list[dict] = []
    for issue in normalized:
        key = issue["issue_key"]
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(issue)

    # Quality trajectory
    scores = get_quality_trajectory(workspace_root)
    scores.append(quality_score)
    trajectory = assess_trajectory(scores)

    # Log iteration
    log_iteration(
        workspace_root,
        iteration=iteration,
        stage="reflection",
        changes=f"{len(deduped)} issues found",
        issues_found=len(deduped),
        issues_fixed=sum(1 for i in deduped if i.get("status") == "fixed"),
        quality_score=quality_score,
    )

    # Log evolution event
    log_evolution_event(workspace_root, deduped, [], trajectory)

    # Generate overlays
    overlays_dir = workspace_root / ".tao" / "project" / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    agents = ["experimenter", "planner", "writer", "editor", "critic", "supervisor", "innovator"]
    overlay_count = 0
    for agent in agents:
        overlay = generate_agent_overlay(agent, deduped)
        if overlay:
            (overlays_dir / f"{agent}.md").write_text(overlay, encoding="utf-8")
            overlay_count += 1

    return {
        "issues_found": len(deduped),
        "trajectory": trajectory,
        "overlays_generated": overlay_count,
    }
