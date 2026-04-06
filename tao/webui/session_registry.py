"""Session registry for tracking active Claude Code sessions."""
from __future__ import annotations
import json
import time
from pathlib import Path


class SessionRegistry:
    """Tracks active Claude Code sessions for projects."""

    def __init__(self, data_dir: str | Path = "~/.tao/sessions") -> None:
        self._dir = Path(data_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    def register(self, project_name: str, session_id: str) -> None:
        data = {"session_id": session_id, "project": project_name, "ts": time.time()}
        (self._dir / f"{project_name}.json").write_text(json.dumps(data))

    def unregister(self, project_name: str) -> None:
        f = self._dir / f"{project_name}.json"
        if f.exists():
            f.unlink()

    def get_session(self, project_name: str) -> dict | None:
        f = self._dir / f"{project_name}.json"
        if not f.exists():
            return None
        return json.loads(f.read_text())

    def list_active(self) -> list[dict]:
        sessions = []
        for f in self._dir.glob("*.json"):
            try:
                sessions.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                pass
        return sessions
