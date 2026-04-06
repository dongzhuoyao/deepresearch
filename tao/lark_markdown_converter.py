"""Deterministic Markdown to Feishu/Lark blocks converter."""
from __future__ import annotations
from typing import Any


def markdown_to_lark_blocks(markdown: str) -> list[dict]:
    """Convert markdown to Feishu document blocks.

    Stub implementation — full version needs lark-oapi types.
    """
    blocks = []
    for line in markdown.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"type": "heading1", "content": line[2:]})
        elif line.startswith("## "):
            blocks.append({"type": "heading2", "content": line[3:]})
        elif line.startswith("### "):
            blocks.append({"type": "heading3", "content": line[4:]})
        elif line.startswith("- "):
            blocks.append({"type": "bullet", "content": line[2:]})
        else:
            blocks.append({"type": "text", "content": line})
    return blocks
