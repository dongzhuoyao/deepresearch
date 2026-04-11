# Start Research Pipeline

**Usage:** `/start <workspace_path>`

Launch the autonomous 18-stage research pipeline from the beginning.

## Steps

1. Read workspace status:
   ```bash
   python3 -c "from tao.orchestrate import cli_status; print(cli_status('$ARGUMENTS'))"
   ```

2. Enter the orchestration loop:
   - Call `cli_next` to get the next action
   - Execute the action (skill, team, bash, or experiment_wait)
   - Call `cli_record` with the result
   - Repeat until stage is "done"

3. The loop is autonomous — no human intervention needed between stages.

4. If interrupted, use `/continue` or `/resume` to pick up where you left off.
