---
name: start
description: Launch autonomous research pipeline
allowed-tools: ["Bash", "Read", "Write", "Agent"]
---

# Start Research Pipeline

**Usage:** `/deepresearch:start <workspace_path>`

## Steps

1. Read workspace status:
   ```bash
   .venv/bin/python3 -c "from sibyl.orchestrate import cli_status; print(cli_status('$ARGUMENTS'))"
   ```

2. Enter the orchestration loop:
   - Call `cli_next` to get the next action
   - Execute the action (skill, team, bash, or experiment_wait)
   - Call `cli_record` with the result
   - Repeat until stage is "done"

3. The loop is autonomous — no human intervention needed between stages.

4. If interrupted, use `/deepresearch:resume` to continue.
