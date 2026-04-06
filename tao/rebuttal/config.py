"""Rebuttal pipeline configuration."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RebuttalConfig:
    max_rounds: int = 3
    score_threshold: float = 7.0
    language: str = "en"
    codex_review_enabled: bool = False
