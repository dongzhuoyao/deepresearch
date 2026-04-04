# DeepResearch (Sibyl Architecture)

Autonomous AI Research System that takes a research topic and produces a complete academic paper -- literature review, novel idea generation, experiment design, GPU-based execution, statistical analysis, and LaTeX compilation -- with zero human intervention.

Built on **Claude Code** as the agent runtime and **RunPod** for GPU compute.

## Architecture Overview

### Dual-Loop Design

**Inner loop** (per-project): An 18-stage pipeline advances a single research project from topic to paper. A state machine governs transitions, with pivot and refine branches when quality gates fail.

**Outer loop** (cross-project): After each project, a reflection + evolution pass extracts lessons learned and patches system prompts and configuration for future runs.

### Multi-Agent Orchestration

The system uses 34 specialized agents (literature researcher, innovator, experimenter, critic, etc.) coordinated by the `FarsOrchestrator`. Agents communicate exclusively through workspace files -- no shared memory, no message passing. The orchestrator generates deterministic `Action` objects that are rendered into execution scripts for Claude Code to run.

### RunPod-Native Compute

All experiments execute on RunPod GPU pods. The GPU scheduler handles task parallelization with topological dependency sorting, and the experiment recovery system detects crashes and resynchronizes state.

## Pipeline Stages

```
init --> literature_search --> idea_debate --> planning --> pilot_experiments
  --> idea_validation_decision --> experiment_cycle --> result_debate
  --> experiment_decision --> writing_outline --> writing_sections
  --> writing_integrate --> writing_final_review --> writing_latex
  --> review --> reflection --> quality_gate --> done
```

| Stage | What happens |
|-------|-------------|
| `init` | Create workspace, write topic and config files |
| `literature_search` | Search arXiv for related work, build literature map |
| `idea_debate` | 6-agent team debates research ideas (innovator, pragmatist, contrarian, etc.) |
| `planning` | Generate experiment plan with baselines and ablations |
| `pilot_experiments` | Quick validation runs on small data |
| `idea_validation_decision` | Decide: proceed, pivot, or refine based on pilots |
| `experiment_cycle` | Full experiment runs on RunPod GPUs |
| `result_debate` | Multi-agent team analyzes results |
| `experiment_decision` | Decide: more experiments or move to writing |
| `writing_outline` | Generate paper outline |
| `writing_sections` | Write individual sections (parallel or sequential) |
| `writing_integrate` | Merge sections, ensure coherence |
| `writing_final_review` | Final quality pass |
| `writing_latex` | Compile Markdown to LaTeX to PDF |
| `review` | Simulated peer review |
| `reflection` | Extract lessons, score quality |
| `quality_gate` | Pass (done) or loop back for revision |
| `done` | Paper complete |

## Quick Start

### 1. Install

```bash
git clone https://github.com/your-username/deepresearch.git
cd deepresearch
pip install -e ".[dev]"
```

### 2. Configure

```bash
# Set API keys
export RUNPOD_API_KEY="your-runpod-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Create project config
cp config.example.yaml config.yaml
# Edit config.yaml to set RunPod GPU type, spot pricing, etc.
```

### 3. Initialize a Research Project

```bash
sibyl init "Improving chain-of-thought reasoning with self-consistency"
```

This creates a workspace directory under `workspaces/` with the topic, config, and initial state files.

### 4. Run the Pipeline

Use the Claude Code plugin commands within a Claude Code session:

```
/start           # Begin pipeline execution
/continue        # Resume from current stage
/status          # Check progress
/pivot           # Force a pivot to a new idea
/stop            # Gracefully stop
```

Or use the CLI for monitoring:

```bash
sibyl status ./workspaces/your_project
sibyl experiment-status ./workspaces/your_project
sibyl dashboard ./workspaces/your_project
```

## Configuration Reference

All settings live in `config.yaml` (project-level) or `config.example.yaml` (template).

| Setting | Default | Description |
|---------|---------|-------------|
| `compute_backend` | `runpod` | Compute backend (always RunPod) |
| `runpod_gpu_type` | `NVIDIA A100 80GB PCIe` | GPU type for pods |
| `runpod_max_pods` | `4` | Maximum concurrent pods |
| `runpod_spot` | `true` | Use spot/preemptible instances |
| `runpod_cloud_type` | `COMMUNITY` | RunPod cloud type |
| `research_focus` | `3` | 1=explore (pivot early), 5=deep focus (persist) |
| `writing_mode` | `parallel` | `parallel`, `sequential`, or `codex` |
| `idea_exp_cycles` | `6` | Max idea-experiment iterations |
| `max_iterations` | `10` | Max pipeline iterations before forced stop |
| `experiment_timeout` | `300` | Seconds before experiment timeout |
| `evolution_enabled` | `true` | Enable cross-project self-improvement |
| `self_heal_enabled` | `true` | Enable automatic error recovery |
| `model_tiers.heavy` | `claude-opus-4-6` | Model for complex reasoning tasks |
| `model_tiers.standard` | `claude-opus-4-6` | Model for standard tasks |
| `model_tiers.light` | `claude-sonnet-4-6` | Model for simple/fast tasks |

## Plugin Commands

The Claude Code plugin provides 9 slash commands:

| Command | Description |
|---------|-------------|
| `/init` | Initialize a new research workspace |
| `/start` | Begin pipeline execution from init stage |
| `/continue` | Resume pipeline from current stage |
| `/status` | Show pipeline status, stage, and errors |
| `/resume` | Resume a stopped or crashed session |
| `/pivot` | Force pivot to a new research direction |
| `/evolve` | Trigger cross-project evolution pass |
| `/debug` | Diagnose and fix pipeline errors |
| `/stop` | Gracefully stop the pipeline |

Three lifecycle hooks run automatically:
- `on-session-start.sh` -- Load workspace context on session start
- `on-bash-complete.sh` -- Post-process bash command results
- `on-stop.sh` -- Clean up on session end

## Self-Healing

The system has a three-tier error recovery strategy:

1. **Mechanical auto-fix** (`auto_fix.py`): Handles common failures like missing pip packages, malformed YAML, and file permission errors.
2. **Skill-based repair** (`self_heal.py`): Routes complex errors to specialized repair agents with a retry budget.
3. **Circuit breaker**: After repeated failures on the same error, the system stops retrying and logs the issue for human review.

## Project Structure

```
sibyl/                      # Main Python package
├── orchestrate.py          # FarsOrchestrator (main API)
├── workspace.py            # Filesystem communication hub
├── config.py               # YAML config with defaults
├── cli.py                  # Typer CLI (sibyl command)
├── compute/                # RunPod compute backend
├── orchestration/          # State machine, lifecycle, action dispatch
├── gpu_scheduler.py        # Parallel task scheduling
├── experiment_recovery.py  # Crash detection and state sync
├── auto_fix.py             # Mechanical error fixes
├── self_heal.py            # Error routing + circuit breaker
├── reflection.py           # Quality trajectory tracking
├── evolution.py            # Cross-project self-improvement
├── latex_pipeline.py       # Markdown -> LaTeX -> PDF
├── prompts/                # 29 agent prompt templates
├── dashboard/              # Flask monitoring dashboard
├── webui/                  # WebUI backend (Flask + WebSocket)
└── rebuttal/               # 7-stage rebuttal pipeline
plugin/                     # Claude Code plugin
├── commands/               # 9 slash commands
└── hooks/scripts/          # 3 lifecycle hooks
.claude/
├── agents/                 # 34 agent definitions (YAML)
└── skills/                 # 34 skill definitions (Markdown)
config.example.yaml         # Configuration template
pyproject.toml              # Package metadata and dependencies
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type check
mypy sibyl

# Lint
ruff check sibyl

# Run demo (no API keys needed)
python -m sibyl.demo
```

## Tech Stack

- **Runtime**: Claude Code (agent execution)
- **Compute**: RunPod (GPU pods via API + SSH)
- **Language**: Python 3.11+
- **Config**: PyYAML + Pydantic-style validation
- **CLI**: Typer + Rich
- **Dashboard**: Flask + Flask-Sock (WebSocket)
- **LaTeX**: pdflatex pipeline
- **Scheduling**: Topological sort with GPU affinity

## License

MIT
