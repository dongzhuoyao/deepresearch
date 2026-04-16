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


_CLAIM = re.compile(
    r"[^.\n!?]*?"
    r"(?:improve|outperform|surpass|state[- ]of[- ]the[- ]art|SOTA"
    r"|\d+(?:\.\d+)?\s*%"
    r"|\+\d+(?:\.\d+)?(?:\s*(?:point|pt|pts|%))?"
    r"|\ba[ct]+uracy of\s+\d"
    r"|reaches?\s+\d+(?:\.\d+)?\s*%)"
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
