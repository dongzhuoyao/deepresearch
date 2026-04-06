"""Prompt helpers for rebuttal agents."""
from __future__ import annotations


def format_review_context(reviews: list[dict]) -> str:
    """Format reviewer comments for agent prompts."""
    lines = ["# Reviewer Comments\n"]
    for i, review in enumerate(reviews, 1):
        reviewer = review.get("reviewer", f"Reviewer {i}")
        score = review.get("score", "N/A")
        comments = review.get("comments", "")
        lines.append(f"## {reviewer} (Score: {score})\n")
        lines.append(comments)
        lines.append("")
    return "\n".join(lines)


def format_rebuttal_prompt(
    review_context: str,
    strategy: str = "",
    prior_draft: str = "",
    feedback: str = "",
) -> str:
    """Build a complete rebuttal prompt."""
    sections = [review_context]
    if strategy:
        sections.append(f"\n## Rebuttal Strategy\n\n{strategy}")
    if prior_draft:
        sections.append(f"\n## Previous Draft\n\n{prior_draft}")
    if feedback:
        sections.append(f"\n## Simulated Reviewer Feedback\n\n{feedback}")
    return "\n".join(sections)
