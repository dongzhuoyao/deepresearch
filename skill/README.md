# DeepResearch Skill Install

This folder contains the portable `deepresearch` skill for Tao. It is designed to work in both Codex and Claude-style environments by relying on the repo's Python entrypoints instead of host-specific slash commands.

## What Gets Installed

- `SKILL.md`: skill contract and workflow
- `run.py`: host-neutral helper CLI
- `references/stages.md`: stage and workspace reference

## Prerequisites

- Python 3.11+
- A local clone of this repository
- Optional for GPU stages: `RUNPOD_API_KEY`
- Optional depending on configured models: `ANTHROPIC_API_KEY`

## Repo Setup

From the repository root:

```bash
pip install -e ".[dev]"
```

This makes the `tao` / `deepresearch` CLI available and ensures `skill/run.py` can call the underlying orchestrator.

## Install In Codex

Copy or symlink this folder into your Codex skills directory as `deepresearch`:

```bash
mkdir -p "$CODEX_HOME/skills"
ln -s "$(pwd)/skill" "$CODEX_HOME/skills/deepresearch"
```

If you do not want a symlink, copy it instead:

```bash
mkdir -p "$CODEX_HOME/skills/deepresearch"
cp -R skill/* "$CODEX_HOME/skills/deepresearch/"
```

After that, Codex can use the `deepresearch` skill when the task matches its description.

## Use From Codex

Typical commands the skill will run:

```bash
python skill/run.py init --topic "research topic"
python skill/run.py status --workspace workspaces/<workspace>
python skill/run.py next --workspace workspaces/<workspace>
python skill/run.py record --workspace workspaces/<workspace> --stage init --result "done" --score 8
python skill/run.py render-prompt --workspace workspaces/<workspace> --skill planner
```

## Use From Claude-Style Hosts

No separate install step is required if you run the host inside this repository.

- `.claude/skills/*` already resolve through `tao.orchestrate`
- `.claude/commands/*` already resolve through `tao.orchestrate`
- the portable helper is still available at `python skill/run.py ...`

## Verify Install

Run:

```bash
python skill/run.py --help
python skill/run.py evolve --workspace . --mode show
```

If both commands work, the skill files and Python entrypoints are wired correctly.

## Notes

- The workspace is the source of truth. Inspect `status` and `next` before acting.
- The skill is portable, but actual experiment stages can still require credentials, RunPod access, and paid GPU execution.
