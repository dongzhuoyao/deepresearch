---
name: stop
description: Pause the research pipeline
allowed-tools: ["Bash", "Read", "Write"]
---

# Stop Research Pipeline

**Usage:** `/deepresearch:stop <workspace_path>`

## Steps

1. Set `stop_requested: true` in workspace status.json.
2. The orchestration loop will stop at the next safe checkpoint.
3. Running experiments will continue to completion on RunPod.
