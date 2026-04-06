"""Feishu/Lark document sync (optional feature)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def sync_to_lark(
    workspace_root: str | Path,
    stage: str,
    content: str,
    config: dict | None = None,
) -> dict:
    """Sync workspace artifacts to Feishu/Lark.

    This is a stub — full implementation requires lark-oapi SDK.
    Returns sync result dict.
    """
    from tao.orchestration.constants import SYNC_SKIP_STAGES

    if stage in SYNC_SKIP_STAGES:
        return {"synced": False, "reason": f"Stage '{stage}' is in skip list"}

    # Queue sync request
    root = Path(workspace_root)
    queue_dir = root / "lark_sync"
    queue_dir.mkdir(parents=True, exist_ok=True)

    import time
    entry = {
        "ts": time.time(),
        "stage": stage,
        "content_length": len(content),
    }
    queue_file = queue_dir / f"sync_{stage}_{int(time.time())}.json"
    queue_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    return {"synced": True, "queued": str(queue_file)}


def is_sync_enabled(config: dict | None = None) -> bool:
    """Check if Lark sync is enabled."""
    if config is None:
        return False
    return config.get("lark_enabled", False)
