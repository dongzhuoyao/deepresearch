"""Frozen research-contract artifact.

A contract locks in hypothesis + independent success/failure signals + ablations.
Once experiments begin it is frozen; modifications require a new version (v2, v3, ...)
with a changelog.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.workspace import Workspace


CONTRACT_PATH = "plan/contract.json"
CONTRACT_LOCK_PATH = "plan/contract.lock"


class ContractError(Exception):
    """Raised on contract validation, save, or load failures."""


@dataclass
class Signal:
    id: str
    description: str

    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        return cls(id=data["id"], description=data["description"])


@dataclass
class ResearchContract:
    version: str
    hypothesis: str
    success_signals: list[Signal]
    failure_signals: list[Signal]
    ablations: list[Signal] = field(default_factory=list)
    changelog: str = ""

    def validate(self) -> None:
        if not self.hypothesis.strip():
            raise ContractError("hypothesis must be non-empty")
        if not self.success_signals:
            raise ContractError("at least one success_signal is required")
        if not self.failure_signals:
            raise ContractError("at least one failure_signal is required")
        # Failure signals must be independent of success signals —
        # reject if a failure is merely the negation of a success.
        for f in self.failure_signals:
            for s in self.success_signals:
                if _is_mere_negation(s.description, f.description):
                    raise ContractError(
                        f"failure signal {f.id!r} is not independent of success "
                        f"signal {s.id!r}: it merely negates the same metric"
                    )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "hypothesis": self.hypothesis,
            "success_signals": [s.to_dict() for s in self.success_signals],
            "failure_signals": [s.to_dict() for s in self.failure_signals],
            "ablations": [s.to_dict() for s in self.ablations],
            "changelog": self.changelog,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchContract":
        return cls(
            version=data["version"],
            hypothesis=data["hypothesis"],
            success_signals=[Signal.from_dict(s) for s in data.get("success_signals", [])],
            failure_signals=[Signal.from_dict(s) for s in data.get("failure_signals", [])],
            ablations=[Signal.from_dict(s) for s in data.get("ablations", [])],
            changelog=data.get("changelog", ""),
        )


# Matches "<lhs> <op> <rhs>" where op is one of ==, !=, >=, <=, >, <.
# Order matters: multi-char ops first so ">=" doesn't match as ">".
_COMPARISON_RE = re.compile(r"^\s*(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")

# Pairs of operators that are direct negations of each other.
_NEGATION_PAIRS = {
    (">=", "<"),
    ("<", ">="),
    (">", "<="),
    ("<=", ">"),
    ("==", "!="),
    ("!=", "=="),
}


def _is_mere_negation(a: str, b: str) -> bool:
    """Return True if `b` merely negates `a` on the same metric core.

    Detects pairs like "acc >= 0.8" vs "acc < 0.8" (and >/<= counterparts):
    same left-hand side, same right-hand side, opposite comparison operators.
    """
    ma = _COMPARISON_RE.match(a)
    mb = _COMPARISON_RE.match(b)
    if not ma or not mb:
        return False
    lhs_a, op_a, rhs_a = (g.strip() for g in ma.groups())
    lhs_b, op_b, rhs_b = (g.strip() for g in mb.groups())
    if lhs_a != lhs_b or rhs_a != rhs_b:
        return False
    return (op_a, op_b) in _NEGATION_PAIRS


def save_contract(ws: "Workspace", contract: ResearchContract) -> Path:
    """Persist contract to workspace. Validates first.

    If a lock file exists and the incoming contract shares the saved version,
    refuse the write — bump version with a changelog to modify.
    """
    contract.validate()
    if ws.file_exists(CONTRACT_LOCK_PATH):
        existing = ws.read_json(CONTRACT_PATH)
        if existing is not None and existing.get("version") == contract.version:
            raise ContractError(
                "contract is frozen — bump version (e.g. v2) with changelog to modify"
            )
    return ws.write_json(CONTRACT_PATH, contract.to_dict())


def load_contract(ws: "Workspace") -> ResearchContract:
    """Load contract from workspace. Raises ContractError if missing."""
    data = ws.read_json(CONTRACT_PATH)
    if data is None:
        raise ContractError(f"contract not found at {CONTRACT_PATH}")
    return ResearchContract.from_dict(data)


def freeze_contract(ws: "Workspace") -> None:
    """Mark the contract as frozen. Idempotent."""
    ws.write_file(CONTRACT_LOCK_PATH, "frozen")
