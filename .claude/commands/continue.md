# Continue Research Pipeline

**Usage:** `/continue <workspace_path>`

Resume an interrupted research pipeline from its current stage.

## Steps

1. Read current status and determine where we left off:
   ```bash
   python3 -c "from tao.orchestrate import cli_status; print(cli_status('$ARGUMENTS'))"
   ```

2. Resume the orchestration loop from the current stage. Same as `/start` but picks up where we stopped.
