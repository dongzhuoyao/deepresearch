# DeepResearch (Tao Architecture)

Autonomous AI Research System -- from idea to paper, zero human intervention. RunPod-native compute.

## Project Structure

```
tao/                        # Main package
├── __init__.py
├── _paths.py               # Path resolution
├── config.py               # YAML-based configuration
├── workspace.py            # Filesystem communication hub
├── orchestrate.py          # Main orchestrator (FarsOrchestrator)
├── cli.py                  # Typer CLI
├── compute/                # Compute backends
│   ├── base.py             # Abstract ComputeBackend (15 abstract methods)
│   └── runpod_backend.py   # RunPod API + SSH (pod lifecycle, remote exec, file transfer)
├── orchestration/          # Pipeline orchestration
│   ├── models.py           # Action, AgentTask dataclasses
│   ├── constants.py        # PIPELINE_STAGES (20 stages)
│   ├── state_machine.py    # Transitions, pivots, quality gates
│   ├── lifecycle.py        # Action generation per stage
│   ├── action_dispatcher.py # Action -> execution script
│   ├── prompt_loader.py    # Dynamic prompt compilation
│   ├── context_builder.py  # Priority-based context packing
│   ├── simple_actions.py   # Single-skill action builders
│   ├── team_actions.py     # Multi-agent team builders
│   ├── experiment_actions.py # Experiment action builders
│   ├── writing_artifacts.py  # Writing action builders
│   ├── review_artifacts.py   # Review action builders
│   ├── reflection_postprocess.py # Post-reflection evolution hook
│   ├── checkpointing.py     # Pipeline checkpoint/restore
│   ├── config_helpers.py    # Config utilities
│   ├── common_utils.py      # Shared orchestration helpers
│   ├── workspace_paths.py   # Workspace path constants
│   ├── dashboard_data.py   # Dashboard data generation
│   ├── cli_core.py         # CLI helpers
│   ├── runtime_cli.py      # Runtime CLI commands
│   ├── project_cli.py      # Project management CLI
│   ├── ops_cli.py          # Operations CLI
│   └── migration_cli.py    # Migration utilities
├── gpu_scheduler.py        # Task parallelization, topological sort
├── experiment_recovery.py  # Crash detection, state sync
├── experiment_records.py   # JSONL experiment database
├── auto_fix.py             # Mechanical fixes (pip install, YAML)
├── self_heal.py            # Error routing, circuit breaker
├── error_collector.py      # Error aggregation
├── event_logger.py         # Structured event logging
├── experiment_digest.py    # Experiment summary generation
├── orchestra_skills.py     # External skill loading
├── lark_sync.py            # Lark document sync
├── lark_markdown_converter.py # Lark <-> Markdown conversion
├── demo.py                 # Dry-run demo of full pipeline
├── reflection.py           # Iteration logging, quality trajectory
├── evolution.py            # Cross-project self-improvement
├── runtime_assets.py       # .claude/ setup, CLAUDE.md generation
├── latex_pipeline.py       # Markdown -> LaTeX -> PDF
├── latex_linter.py         # LaTeX quality checks
├── prompts/                # 35 agent prompt templates
├── dashboard/server.py     # Flask dashboard
├── webui/                  # WebUI backend (Flask + WebSocket)
└── rebuttal/               # Rebuttal pipeline (7-stage)
plugin/                     # Claude Code plugin
├── commands/               # 9 skill commands
└── hooks/scripts/          # 3 lifecycle hooks
.claude/agents/             # 35 agent definitions (YAML)
.claude/skills/             # 34 skill definitions (Markdown)
```

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# CLI
tao status .
tao init "research topic"
tao cli-record . <stage> <result> <score>  # record result, advance pipeline
tao experiment-status .
tao dispatch .
tao evolve . --show
tao self-heal-scan .
tao latex-compile .
tao dashboard .
tao webui --port 3000       # web dashboard UI
tao serve --port 3000       # API-only server

# Run demo
python -m tao.demo
```

## Pipeline (20 stages)

init -> literature_search -> idea_debate -> planning -> pilot_experiments
-> idea_validation_decision -> experiment_cycle -> result_debate
-> experiment_decision -> writing_outline -> writing_assets
-> writing_sections -> writing_integrate -> writing_teaser
-> writing_final_review -> writing_latex -> review -> reflection
-> quality_gate -> done

## Key Patterns

- **State machine**: Deterministic transitions with pivot/refine/quality-gate loops
- **Workspace as hub**: All agents communicate via workspace files (JSON + Markdown)
- **Action dispatch**: Orchestrator generates Action -> rendered to execution script
- **Dual loop**: Inner (research iteration) + Outer (self-evolution across projects)
- **RunPod compute**: All experiments run on RunPod GPU pods
- **Self-healing**: Mechanical auto-fix -> skill-based repair -> circuit breaker
- **Multi-agent teams**: 6-agent debates for ideas and results
- **Prompt compilation**: Base template + overlays + project memory + evolution lessons

## Environment Variables

```bash
RUNPOD_API_KEY=...
ANTHROPIC_API_KEY=...
TAO_ROOT=...  # optional: override repo root detection
```

## SSH / RunPod

- Private key: `~/.ssh/id_ed25519`
- Always use `cloud_type: SECURE` (never COMMUNITY)
- Always use `template_id: runpod-torch-v240` — pre-cached image, boots in ~30s vs 10+ min
- Web dashboard default port: 3000 (range 3000-3002)
- RunPod storage: code and data go to `/workspace/` (persists across pod restarts)
- Proxy SSH username is `podHostId` from API (not raw pod_id) — query `machine.podHostId`

## Config

Edit `config.example.yaml` and copy to `config.yaml`. Key settings:
- `compute_backend: runpod` (always RunPod)
- `runpod_template_id: runpod-torch-v240` (pre-cached, fast boot)
- `runpod_cloud_type: SECURE` (always)
- `runpod_image` — must match GPU arch (see Gotchas for Blackwell)
- `runpod_gpu_type`, `runpod_max_pods`, `runpod_spot`
- `research_focus: 1-5` (explore <-> deep focus)
- `writing_mode: parallel|sequential|codex`
- `evolution_enabled`, `self_heal_enabled`

## Development

- Old Python-only pipeline preserved on `python` branch (pre-Tao architecture)
- Reference architecture: github.com/Sibyl-Research-Team/AutoResearch-SibylSystem
- Package is `tao/` (top-level, not under `src/`)
- Tests: `pytest tests/ -v` — 287 tests, all run in <0.3s (no API calls)
- Demo: `python -m tao.demo` — dry-run of full 20-stage pipeline
- Plugin dev: `claude --plugin-dir ./plugin --dangerously-skip-permissions`
- Agent defs: `.claude/agents/*.yml` (YAML with name, model, description)
- Skill defs: `.claude/skills/*.md` (markdown with shebang to render_skill_prompt)
- Compute is RunPod-only — full pod lifecycle via `RunPodBackend` (create, stop, wait_for_ready, run_remote, upload/download, terminate)
- CLI aliases: `tao` and `deepresearch` both work (same entry point)
- Two SSH modes: "full" (public IP, supports rsync/scp) and "basic" (proxied via ssh.runpod.io, tar fallback for file transfer)
- Workspace is the communication hub — agents never talk directly, only via files

## Gotchas

- **Blackwell GPU + PyTorch image** — RTX PRO 4500/5090/B100 (sm_120) need `runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04`; the default 2.4.0 image only supports up to sm_90 (Hopper). Wrong image → `CUDA error: no kernel image available`
- **RunPod costs money** — terminate pods immediately when idle; prepare everything locally before spinning up a pod
- **RunPod storage** — only `/workspace/` persists; files outside it are lost on pod restart
- **Prefer GPU-light methods** — few-step fine-tune, LoRA, small models over heavy training runs
- **State machine** — check test_state_machine.py before modifying transitions
- **RunPod image pull** — without `template_id`, image pulls take 10+ min even for the same image; always set `template_id` in config

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
