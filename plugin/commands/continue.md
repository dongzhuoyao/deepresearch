---
name: continue
description: Continue an interrupted research pipeline
allowed-tools: ["Bash", "Read", "Write", "Agent"]
---

# Continue Research Pipeline

**Usage:** `/deepresearch:continue <workspace_path>`

## Steps

1. Read current status and determine where we left off:
   ```bash
   .venv/bin/python3 -c "from tao.orchestrate import cli_status; print(cli_status('$ARGUMENTS'))"
   ```

2. Resume the orchestration loop from the current stage.

3. Same as `/deepresearch:start` but picks up where we stopped.
