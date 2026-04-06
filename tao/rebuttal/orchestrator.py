"""Rebuttal pipeline orchestrator."""
from __future__ import annotations
import json
import time
from pathlib import Path

from tao.rebuttal.config import RebuttalConfig
from tao.rebuttal.state_machine import RebuttalStateMachine
from tao.rebuttal.workspace_setup import setup_rebuttal_workspace
from tao.rebuttal.scoring import compute_rebuttal_score, track_score_trajectory


class RebuttalOrchestrator:
    """Orchestrates the rebuttal pipeline."""

    def __init__(self, workspace_root: str | Path, config: RebuttalConfig | None = None) -> None:
        self._root = Path(workspace_root)
        self._cfg = config or RebuttalConfig()
        self._sm = RebuttalStateMachine(
            max_rounds=self._cfg.max_rounds,
            score_threshold=self._cfg.score_threshold,
        )
        self._state_file = self._root / "rebuttal" / "state.json"

    def init(self, reviews: list[dict]) -> str:
        """Initialize rebuttal pipeline with reviewer comments."""
        setup_rebuttal_workspace(self._root)

        # Save reviews
        reviews_file = self._root / "rebuttal" / "reviews" / "reviews.json"
        reviews_file.write_text(json.dumps(reviews, indent=2, ensure_ascii=False))

        # Initialize state
        state = {
            "stage": "parse_reviews",
            "round": 0,
            "scores": [],
            "started_at": time.time(),
        }
        self._save_state(state)
        return "parse_reviews"

    def get_stage(self) -> str:
        state = self._load_state()
        return state.get("stage", "done")

    def record_result(self, stage: str, result: str = "", score: float = 0.0) -> str:
        """Record result and advance stage."""
        state = self._load_state()

        if stage == "score_evaluate":
            state["scores"].append(score)
            state["round"] += 1

        next_stage = self._sm.next_stage(
            stage,
            score=score,
            round_num=state.get("round", 0),
        )
        state["stage"] = next_stage
        self._save_state(state)
        return next_stage

    def is_done(self) -> bool:
        return self._sm.is_done(self.get_stage())

    def get_status(self) -> dict:
        state = self._load_state()
        return {
            "stage": state.get("stage", "done"),
            "round": state.get("round", 0),
            "scores": state.get("scores", []),
            "trajectory": track_score_trajectory(state.get("scores", [])),
        }

    def _load_state(self) -> dict:
        if not self._state_file.exists():
            return {"stage": "done", "round": 0, "scores": []}
        return json.loads(self._state_file.read_text())

    def _save_state(self, state: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state, indent=2))
