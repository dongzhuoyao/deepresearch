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
│   ├── base.py             # Abstract ComputeBackend (11 abstract methods)
│   └── runpod_backend.py   # RunPod API + SSH (pod lifecycle, remote exec, file transfer)
├── orchestration/          # Pipeline orchestration
│   ├── models.py           # Action, AgentTask dataclasses
│   ├── constants.py        # PIPELINE_STAGES (18 stages)
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
│   ├── dashboard_data.py   # Dashboard data generation
│   └── cli_core.py         # CLI helpers
├── gpu_scheduler.py        # Task parallelization, topological sort
├── experiment_recovery.py  # Crash detection, state sync
├── experiment_records.py   # JSONL experiment database
├── auto_fix.py             # Mechanical fixes (pip install, YAML)
├── self_heal.py            # Error routing, circuit breaker
├── reflection.py           # Iteration logging, quality trajectory
├── evolution.py            # Cross-project self-improvement
├── runtime_assets.py       # .claude/ setup, CLAUDE.md generation
├── latex_pipeline.py       # Markdown -> LaTeX -> PDF
├── prompts/                # 29 agent prompt templates
├── dashboard/server.py     # Flask dashboard
├── webui/                  # WebUI backend (Flask + WebSocket)
└── rebuttal/               # Rebuttal pipeline (7-stage)
plugin/                     # Claude Code plugin
├── commands/               # 9 skill commands
└── hooks/scripts/          # 3 lifecycle hooks
.claude/agents/             # 34 agent definitions (YAML)
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
tao experiment-status .
tao dispatch .
tao evolve . --show
tao self-heal-scan .
tao latex-compile .
tao dashboard .

# Run demo
python -m tao.demo
```

## Pipeline (18 stages)

init -> literature_search -> idea_debate -> planning -> pilot_experiments
-> idea_validation_decision -> experiment_cycle -> result_debate
-> experiment_decision -> writing_outline -> writing_sections
-> writing_integrate -> writing_final_review -> writing_latex
-> review -> reflection -> quality_gate -> done

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

## Config

Edit `config.example.yaml` and copy to `config.yaml`. Key settings:
- `compute_backend: runpod` (always RunPod)
- `runpod_gpu_type`, `runpod_max_pods`, `runpod_spot`
- `research_focus: 1-5` (explore <-> deep focus)
- `writing_mode: parallel|sequential|codex`
- `evolution_enabled`, `self_heal_enabled`

## Development

- Old Python-only pipeline preserved on `python` branch (pre-Tao architecture)
- Reference architecture: github.com/Sibyl-Research-Team/AutoResearch-SibylSystem
- Package is `tao/` (top-level, not under `src/`)
- Tests: `pytest tests/ -v` — 280 tests, all run in <0.3s (no API calls)
- Demo: `python -m tao.demo` — dry-run of full 18-stage pipeline
- Plugin dev: `claude --plugin-dir ./plugin --dangerously-skip-permissions`
- Agent defs: `.claude/agents/*.yml` (YAML with name, model, description)
- Skill defs: `.claude/skills/*.md` (markdown with shebang to render_skill_prompt)
- Compute is RunPod-only — full pod lifecycle via `RunPodBackend` (create, stop, wait_for_ready, run_remote, upload/download, terminate)
- SSH key auto-detected from `~/.ssh/` (prefers ed25519 > rsa > ecdsa)
- Two SSH modes: "full" (public IP, supports rsync/scp) and "basic" (proxied via ssh.runpod.io, tar fallback for file transfer)
- State machine transitions tested extensively — check test_state_machine.py before modifying
- Workspace is the communication hub — agents never talk directly, only via files
