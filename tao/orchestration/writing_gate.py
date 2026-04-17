"""Writing gate — verify empirical claims cite frozen contract signals.

Every comparative / quantitative claim in the paper must reference a
[signal:<id>] tag that points at a signal declared in plan/contract.json.
This stops the model from inventing story-fits after seeing results
(the post-hoc rationalization failure mode).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from tao.orchestration.contract import ResearchContract


@dataclass
class ClaimViolation:
    claim: str
    reason: str


# A claim is a sentence that makes a *quantified* empirical assertion.
# Bare verbs like "improve" without a number are ambiguous prose, not claims,
# so the trigger must be numeric. This avoids false positives on sentences
# like "We aim to improve readability" or "The model uses +2 layers".
_CLAIM = re.compile(
    r"[^.\n!?]*?"
    r"(?:"
        r"\d+(?:\.\d+)?\s*%"                                       # 82%, 3.5%
        r"|\+?\s*\d+(?:\.\d+)?\s*(?:pt|pts|point|points)\b"         # +5 pts, 3 points
        r"|(?:reach(?:es)?|achieve[sd]?|attains?)\s+\d+(?:\.\d+)?"  # reaches 82, achieves 0.9
        r"|\ba[ct]+uracy of\s+\d+(?:\.\d+)?"                        # accuracy of 98
    r")"
    r"[^.\n!?]*?[.!?]",
    re.IGNORECASE,
)
_SIGNAL_TAG = re.compile(r"\[signal:\s*([a-zA-Z0-9_\-]+)\s*\]")


def verify_claims_against_contract(
    text: str, contract: ResearchContract
) -> list[ClaimViolation]:
    """Scan `text` for empirical claims; flag any without a valid signal tag."""
    ids = {s.id for s in contract.success_signals + contract.failure_signals + contract.ablations}
    violations: list[ClaimViolation] = []
    for match in _CLAIM.finditer(text):
        sentence = match.group(0).strip()
        tags = _SIGNAL_TAG.findall(sentence)
        if not tags:
            violations.append(ClaimViolation(claim=sentence, reason="no [signal:*] tag"))
            continue
        unknown = [t for t in tags if t not in ids]
        if unknown:
            violations.append(ClaimViolation(
                claim=sentence, reason=f"unknown signals: {unknown}"
            ))
    return violations
