---
name: init
description: Initialize a new research workspace
allowed-tools: ["Bash", "Read", "Write", "Agent"]
---

# Initialize Research Workspace

**Usage:** `/deepresearch:init [topic or spec.md path]`

## Steps

1. If the argument is a file path ending in `.md`, read it as a spec:
   ```bash
   .venv/bin/python3 -c "from tao.orchestrate import cli_init_from_spec; print(cli_init_from_spec('$ARGUMENTS'))"
   ```

2. Otherwise, use the argument as a topic:
   ```bash
   .venv/bin/python3 -c "from tao.orchestrate import cli_init; print(cli_init('$ARGUMENTS'))"
   ```

3. Display the created workspace path and initial status.

4. Suggest running `/deepresearch:start` to begin the research pipeline.
