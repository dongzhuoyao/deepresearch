"""Gemini CLI scout — external literature discovery via the `gemini` binary.

Why (from `context_is_all_you_need.md`): Gemini has the widest search coverage
among the main frontier models; using it as a scout keeps the main orchestrator
out of raw web results and preserves context. The scout returns structured
paper records; the orchestrator decides what to read in full.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class ScoutQuery:
    topic: str
    constraints: list[str] = field(default_factory=list)

    def expand(self) -> list[str]:
        """Fan out into multi-angle queries: methods / empirical / surveys."""
        angles = [
            f"{self.topic} — recent methods (top venues, code available)",
            f"{self.topic} — empirical comparisons and benchmarks",
            f"{self.topic} — surveys and taxonomy",
        ]
        if self.constraints:
            suffix = " [" + ", ".join(self.constraints) + "]"
            angles = [a + suffix for a in angles]
        return angles


class GeminiScout:
    def __init__(self, bin_path: str = "gemini", timeout_sec: int = 180) -> None:
        self._bin = bin_path
        self._timeout = timeout_sec

    def available(self) -> bool:
        return shutil.which(self._bin) is not None

    def search(self, topic: str, constraints: list[str] | None = None) -> list[dict]:
        if not self.available():
            return []
        query = ScoutQuery(topic=topic, constraints=constraints or [])
        prompt = (
            "Return strict JSON of the form "
            "{\"papers\":[{\"title\":..,\"url\":..,\"venue\":..,\"has_code\":..}]}. "
            "Search these angles:\n" + "\n".join(f"- {a}" for a in query.expand())
        )
        try:
            result = subprocess.run(
                [self._bin, "-p", prompt],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return []
        papers = data.get("papers", []) if isinstance(data, dict) else []
        return [p for p in papers if isinstance(p, dict)]
