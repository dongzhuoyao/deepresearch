# Debug Utilities

**Usage:** `/debug <workspace_path>`

Diagnose and fix pipeline errors.

## Available Actions

1. **State inspection**: Show full workspace status, experiment state, GPU progress
2. **Error scan**: Run self-heal scan for fixable errors
   ```bash
   python3 -c "from tao.orchestrate import cli_status; print(cli_status('$ARGUMENTS'))"
   ```
3. **Log review**: Show recent events and iteration history
4. **Reset stage**: Manually set the pipeline stage (use with caution)
