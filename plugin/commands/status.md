---
name: status
description: Show research pipeline status
allowed-tools: ["Bash", "Read"]
---

# Pipeline Status

**Usage:** `/deepresearch:status [workspace_path]`

## Steps

1. If workspace_path provided, show that project's status.
2. Otherwise, scan workspaces/ directory for all projects.
3. Display: stage, iteration, quality score, running experiments, errors.

```bash
.venv/bin/python3 -c "from sibyl.orchestrate import cli_status; print(cli_status('$ARGUMENTS' or '.'))"
```
