"""Rebuttal pipeline constants."""

REBUTTAL_STAGES = [
    "parse_reviews",
    "strategy",
    "rebuttal_draft",
    "simulated_review",
    "score_evaluate",
    "final_synthesis",
    "done",
]

MAX_REBUTTAL_ROUNDS = 3
SCORE_THRESHOLD = 7.0
