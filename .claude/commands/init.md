# Initialize Research Workspace

**Usage:** `/init [topic or spec.md path]`

Initialize a new Tao research project. The argument can be either a plain topic string or a path to a spec `.md` file.

## Steps

1. If the argument is a file path ending in `.md`, read it as a spec and initialize from it:
   ```bash
   python3 -c "from tao.orchestrate import cli_init_from_spec; print(cli_init_from_spec('$ARGUMENTS'))"
   ```

2. Otherwise, use the argument as a research topic:
   ```bash
   python3 -c "from tao.orchestrate import cli_init; print(cli_init('$ARGUMENTS'))"
   ```

3. Display the created workspace path and initial status.

4. Suggest running `/start <workspace_path>` to begin the research pipeline.
