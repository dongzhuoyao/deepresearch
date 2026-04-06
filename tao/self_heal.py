"""Self-healing router — routes errors to repair pipelines with circuit breaker."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tao.auto_fix import try_auto_fix


# Error category -> repair skill pipelines
SKILL_ROUTE_TABLE = {
    "import": ["python-patterns", "tdd-workflow"],
    "test": ["systematic-debugging", "tdd-workflow"],
    "type": ["python-patterns", "python-review"],
    "state": ["systematic-debugging", "verification-loop"],
    "config": ["systematic-debugging"],
    "build": ["build-error-resolver", "tdd-workflow"],
    "prompt": None,  # direct fix, no skill needed
}

# Priority order for error categories
CATEGORY_PRIORITY = [
    "import", "build", "type", "test", "state", "config", "prompt",
    "system", "experiment", "writing", "analysis", "planning", "pipeline",
    "ideation", "efficiency",
]


@dataclass
class ErrorEntry:
    """A tracked error with fix attempt history."""
    category: str
    message: str
    first_seen: float = 0.0
    attempts: int = 0
    last_attempt: float = 0.0
    fixed: bool = False
    fix_action: str = ""
    breaker_tripped: bool = False


class SelfHealRouter:
    """Routes errors to repair pipelines with circuit breaker protection."""

    def __init__(self, workspace_root: str | Path, max_attempts: int = 3) -> None:
        self._root = Path(workspace_root)
        self._max_attempts = max_attempts
        self._state_file = self._root / "logs" / "self_heal_state.json"
        self._errors: dict[str, ErrorEntry] = {}
        self._load_state()

    def scan_errors(self) -> list[dict]:
        """Scan for errors from errors.jsonl and return actionable ones."""
        from tao.error_collector import read_errors
        raw_errors = read_errors(self._root / "logs")

        actionable = []
        seen_keys: set[str] = set()
        for err in raw_errors:
            key = self._error_key(err["category"], err["message"])
            if key in seen_keys:
                continue  # dedup within this scan

            entry = self._errors.get(key)

            if entry and entry.fixed:
                continue  # already fixed
            if entry and entry.breaker_tripped:
                continue  # circuit breaker

            if entry is None:
                entry = ErrorEntry(
                    category=err["category"],
                    message=err["message"],
                    first_seen=err.get("ts", time.time()),
                )
                self._errors[key] = entry

            seen_keys.add(key)
            actionable.append({
                "key": key,
                "category": err["category"],
                "message": err["message"],
                "attempts": entry.attempts,
            })

        # Sort by priority
        priority_map = {c: i for i, c in enumerate(CATEGORY_PRIORITY)}
        actionable.sort(key=lambda e: priority_map.get(e["category"], 99))

        return actionable

    def attempt_fix(self, error_key: str) -> dict:
        """Attempt to fix an error. Returns fix result."""
        entry = self._errors.get(error_key)
        if entry is None:
            return {"fixed": False, "action": "none", "details": "Unknown error key"}

        if entry.breaker_tripped:
            return {"fixed": False, "action": "breaker", "details": "Circuit breaker tripped"}

        # Increment attempt counter
        entry.attempts += 1
        entry.last_attempt = time.time()

        # Check circuit breaker
        if entry.attempts > self._max_attempts:
            entry.breaker_tripped = True
            self._save_state()
            return {"fixed": False, "action": "breaker", "details": f"Max attempts ({self._max_attempts}) exceeded"}

        # Try mechanical auto-fix first
        result = try_auto_fix(entry.category, entry.message, str(self._root))

        if result["fixed"]:
            entry.fixed = True
            entry.fix_action = result["action"]

        self._save_state()
        return result

    def get_repair_skills(self, category: str) -> list[str] | None:
        """Get the repair skill pipeline for a category."""
        return SKILL_ROUTE_TABLE.get(category)

    def get_summary(self) -> dict:
        """Get self-heal state summary."""
        total = len(self._errors)
        fixed = sum(1 for e in self._errors.values() if e.fixed)
        tripped = sum(1 for e in self._errors.values() if e.breaker_tripped)
        active = total - fixed - tripped
        return {
            "total": total,
            "fixed": fixed,
            "breaker_tripped": tripped,
            "active": active,
        }

    def reset(self) -> None:
        """Reset all error tracking (fresh start)."""
        self._errors.clear()
        self._save_state()

    def _error_key(self, category: str, message: str) -> str:
        """Generate a dedup key for an error."""
        # Use first 100 chars of message for dedup
        msg_key = message[:100].strip().lower()
        return f"{category}:{msg_key}"

    def _load_state(self) -> None:
        """Load persisted state."""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, encoding="utf-8") as f:
                data = json.load(f)
            for key, entry_data in data.get("errors", {}).items():
                self._errors[key] = ErrorEntry(**entry_data)
        except (json.JSONDecodeError, TypeError):
            pass

    def _save_state(self) -> None:
        """Persist state."""
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "errors": {
                key: {
                    "category": e.category,
                    "message": e.message,
                    "first_seen": e.first_seen,
                    "attempts": e.attempts,
                    "last_attempt": e.last_attempt,
                    "fixed": e.fixed,
                    "fix_action": e.fix_action,
                    "breaker_tripped": e.breaker_tripped,
                }
                for key, e in self._errors.items()
            }
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
