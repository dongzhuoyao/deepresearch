"""Rebuttal quality scoring."""
from __future__ import annotations
from typing import Any


def compute_rebuttal_score(
    reviewer_feedback: dict,
    rebuttal_text: str,
) -> float:
    """Compute a quality score for a rebuttal response.

    Stub: in production, this would use an LLM to score.
    Returns a score 0-10.
    """
    if not rebuttal_text:
        return 0.0

    score = 5.0  # base score

    # Length heuristic
    if len(rebuttal_text) > 500:
        score += 1.0
    if len(rebuttal_text) > 1500:
        score += 1.0

    # Evidence heuristic (mentions data/table/figure)
    evidence_words = ["table", "figure", "data", "result", "experiment", "p-value", "significant"]
    evidence_count = sum(1 for w in evidence_words if w in rebuttal_text.lower())
    score += min(evidence_count * 0.3, 2.0)

    return min(score, 10.0)


def track_score_trajectory(scores: list[float]) -> str:
    """Assess rebuttal quality trajectory."""
    if len(scores) < 2:
        return "insufficient"
    if scores[-1] > scores[-2]:
        return "improving"
    if scores[-1] < scores[-2]:
        return "declining"
    return "stable"
