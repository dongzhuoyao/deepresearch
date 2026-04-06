"""Rebuttal state machine — round-based iteration."""
from __future__ import annotations
from tao.rebuttal.constants import REBUTTAL_STAGES, SCORE_THRESHOLD


class RebuttalStateMachine:
    """State machine for the rebuttal pipeline."""

    def __init__(self, max_rounds: int = 3, score_threshold: float = SCORE_THRESHOLD) -> None:
        self._max_rounds = max_rounds
        self._threshold = score_threshold

    def next_stage(self, current: str, score: float = 0.0, round_num: int = 0) -> str:
        if current == "score_evaluate":
            if score >= self._threshold or round_num >= self._max_rounds:
                return "final_synthesis"
            return "rebuttal_draft"  # iterate

        if current == "final_synthesis":
            return "done"

        try:
            idx = REBUTTAL_STAGES.index(current)
        except ValueError:
            return "done"
        if idx + 1 < len(REBUTTAL_STAGES):
            return REBUTTAL_STAGES[idx + 1]
        return "done"

    def is_done(self, stage: str) -> bool:
        return stage == "done"
