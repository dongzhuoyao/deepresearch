# DeepResearch

Automated AI Research Pipeline for conducting literature research, proposing novel ideas, designing/executing experiments, analyzing results, and generating papers.

## Project Structure

```
src/deepresearch/
├── core/           # Config, state management, exceptions
├── providers/      # AI providers (OpenAI, Anthropic, Google)
├── modules/
│   ├── literature/ # arXiv search, novelty checking
│   ├── ideation/   # Idea generation
│   ├── experiment/ # Design, execution, checkpointing
│   ├── analysis/   # Statistical analysis
│   ├── figures/    # Matplotlib plots, TikZ diagrams
│   ├── vision/     # MNIST/CIFAR datasets, vision experiments
│   └── writing/    # Paper section generation
├── pipeline/       # Research and vision pipeline orchestrators
└── cli/            # Typer CLI (main.py)
```

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type check
mypy src/deepresearch

# Lint
ruff check src/deepresearch

# CLI usage
deepresearch vision "topic" --datasets mnist,cifar10 --samples 100
deepresearch run "topic" --budget 50
deepresearch search "query" --max 20
```

## Key Patterns

- **Providers**: All AI providers extend `BaseProvider` in `providers/base.py`
- **Pipeline stages**: Defined in `pipeline/stage.py`, orchestrated by `research_pipeline.py`
- **Async throughout**: Uses `asyncio` and `aiofiles` for async operations
- **Config**: Hydra-based config in `configs/`, Pydantic models in `core/config.py`
- **State**: Research state managed via `core/state.py` with checkpoint support

## Environment Variables

```bash
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

## Tech Stack

- Python 3.11+
- AI: anthropic, openai, google-generativeai
- Data: numpy, scipy, pandas
- Viz: matplotlib, seaborn
- Config: hydra-core, pydantic
- CLI: typer, rich
- Vision: torch, torchvision
