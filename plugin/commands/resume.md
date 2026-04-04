---
name: resume
description: Resume a paused research pipeline
allowed-tools: ["Bash", "Read", "Write", "Agent"]
---

# Resume Paused Pipeline

**Usage:** `/deepresearch:resume <workspace_path>`

## Steps

1. Clear any pause/stop markers in workspace status.json.
2. Resume the orchestration loop.
