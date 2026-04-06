"""File system watcher for workspace artifact changes."""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Any


def watch_workspace(
    workspace_root: str | Path,
    callback: Callable[[str, str], None],
    patterns: list[str] | None = None,
) -> None:
    """Watch workspace for file changes.

    Uses watchfiles if available, otherwise no-op.
    callback(event_type, file_path) is called for each change.
    """
    try:
        import watchfiles
    except ImportError:
        return  # watchfiles not installed, skip

    root = Path(workspace_root)
    watch_patterns = patterns or ["*.json", "*.md", "*.jsonl"]

    for changes in watchfiles.watch(root, recursive=True):
        for change_type, path in changes:
            rel = Path(path).relative_to(root)
            if any(rel.match(p) for p in watch_patterns):
                callback(change_type.name, str(rel))
