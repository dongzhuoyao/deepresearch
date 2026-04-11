# Pipeline Status

**Usage:** `/status [workspace_path]`

Show the current state of a research pipeline.

## Steps

1. If workspace_path provided, show that project's status.
2. Otherwise, scan `workspaces/` directory for all projects.
3. Display: stage, iteration, quality score, running experiments, errors.

```bash
python3 -c "from tao.orchestrate import cli_status; print(cli_status('$ARGUMENTS' or '.'))"
```
