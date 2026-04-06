"""Human-readable experiment summaries."""
from __future__ import annotations
from pathlib import Path
from tao.experiment_records import load_experiments


def generate_digest(workspace_root: str | Path) -> str:
    """Generate a human-readable experiment digest."""
    records = load_experiments(workspace_root)
    if not records:
        return "No experiments recorded yet."

    lines = [f"# Experiment Digest ({len(records)} experiments)\n"]

    for i, rec in enumerate(records, 1):
        task_id = rec.get("task_id", "unknown")
        metrics = rec.get("metrics", {})
        config = rec.get("config", {})

        lines.append(f"## {i}. {task_id}")
        if config:
            lines.append(f"Config: {_format_dict(config)}")
        if metrics:
            lines.append(f"Metrics: {_format_dict(metrics)}")
        lines.append("")

    return "\n".join(lines)


def _format_dict(d: dict) -> str:
    """Format dict as key=value pairs."""
    parts = [f"{k}={v}" for k, v in d.items()]
    return ", ".join(parts)
