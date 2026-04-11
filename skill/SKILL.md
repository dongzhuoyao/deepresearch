---
name: deepresearch
description: Operate Tao research workspaces end to end. Initialize from a topic or spec, inspect state, fetch the next orchestrator action, record stage results, render specialist Tao prompts, and drive stuck pipelines forward with evidence. Use when the user wants to start, continue, debug, review, or manually advance a DeepResearch workspace.
license: MIT
dependencies:
  runtime:
    - python3
  env:
    - RUNPOD_API_KEY (required for GPU experiment stages)
    - ANTHROPIC_API_KEY (depends on your configured model stack)
---

# DeepResearch

Run Tao like an operating system, not like a chat prompt. The workspace is the source of truth. Inspect state, execute the next justified action, record the result, repeat.

Follow the repo CLI and workspace files, not host-specific slash commands. This skill is designed to work in Codex and Claude-style environments with the same workflow.

## Use This Skill When

- The user wants to initialize a workspace from a topic or `spec.md`
- The user wants to inspect status, continue, resume, or debug a Tao workspace
- The user wants to manually drive the pipeline one stage at a time
- The user wants a Tao role prompt such as `planner`, `experimenter`, or `literature`
- The user wants evidence for whether a workspace is ready to advance

## Setup

```bash
cd <repo-root>
pip install -e ".[dev]"
```

Optional but commonly needed environment variables:

```bash
export RUNPOD_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

## Voice

- Be direct, concrete, and operational.
- Name the workspace, stage, file, and command.
- Avoid filler and vague summaries.
- End with the next action or the blocking fact.

## Completion Status

Use one of these labels when closing the workflow:

- `DONE` — the requested workflow completed and the evidence is clear
- `DONE_WITH_CONCERNS` — completed, but there are risks or unresolved issues
- `BLOCKED` — cannot proceed because the system or environment prevents it
- `NEEDS_CONTEXT` — cannot proceed because the user has not provided a required path, topic, or decision

## Core Workflow

1. Establish the workspace.
   - If there is no workspace, initialize one with `python skill/run.py init --topic "..."` or `--spec-file path/to/spec.md`.
   - If there is a workspace, inspect it first with `python skill/run.py status --workspace <workspace>`.

2. Read the orchestrator before acting.
   - Run `python skill/run.py next --workspace <workspace>`.
   - Treat the returned `stage`, `action_type`, and `execution_script` as the current contract.
   - Do not guess the next stage from memory when the workspace can tell you directly.

3. Execute the smallest justified action.
   - Prefer repo-native commands, tests, workspace files, and Tao prompts over ad hoc prose.
   - For role-specific reasoning, render the prompt with `python skill/run.py render-prompt --workspace <workspace> --skill <role>`.
   - If the stage is blocked by missing credentials, missing infra, or missing files, stop and report that directly.

4. Record the result immediately.
   - Run `python skill/run.py record --workspace <workspace> --stage <stage> --result "..." --score <0-10>`.
   - Never claim a stage is complete without recording it back into the state machine.

5. Re-check state after every material action.
   - Run `status` again after `record`.
   - If the workspace still looks inconsistent, inspect `next` again before doing more work.

## Commands

Use the helper when you want a host-neutral entrypoint:

```bash
python skill/run.py init --topic "Improving chain-of-thought reasoning with self-consistency"
python skill/run.py status --workspace workspaces/<workspace>
python skill/run.py next --workspace workspaces/<workspace>
python skill/run.py record --workspace workspaces/<workspace> --stage init --result "workspace initialized" --score 8
python skill/run.py render-prompt --workspace workspaces/<workspace> --skill planner
python skill/run.py evolve --workspace workspaces/<workspace> --mode show
```

Use direct Tao commands when they are simpler:

```bash
tao status <workspace>
tao experiment-status <workspace>
tao self-heal-scan <workspace>
tao dashboard <workspace>
tao latex-compile <workspace>
```

## Evidence Rules

- Cite the active workspace path in the final report.
- Name the current stage and the next stage when you advance the pipeline.
- If you claim a stage is done, mention the `record` command or the resulting status.
- If you claim something is blocked, name the missing file, credential, service, or state transition.

## Escalation

Stop and report `BLOCKED` or `NEEDS_CONTEXT` when:

- the workspace path is unknown or invalid
- the next action requires credentials or compute that are not available
- the orchestrator state and workspace files disagree
- a stage would incur real GPU cost and the user has not asked you to spend it

## Notes

- `init` accepts either `--topic` or `--spec-file`.
- `status`, `next`, and `record` emit JSON, which makes them safe for either host.
- `render-prompt` uses the same prompt compiler that powers `.claude/skills`.
- If you need the full stage list or common workspace layout, read [references/stages.md](references/stages.md).
