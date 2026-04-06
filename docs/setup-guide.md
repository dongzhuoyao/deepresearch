# Setup Guide

Step-by-step instructions for getting the Tao Research System running.

## Prerequisites

- Python 3.11 or later
- A RunPod account with API access (https://runpod.io)
- An Anthropic API key (https://console.anthropic.com)
- Claude Code CLI installed (https://docs.anthropic.com/en/docs/claude-code)
- Git

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/deepresearch.git
cd deepresearch
```

## 2. Install Dependencies

```bash
# Create a virtual environment (recommended)
python3.11 -m venv .venv
source .venv/bin/activate

# Install the package in development mode
pip install -e ".[dev]"

# Verify installation
tao --help
```

This installs the core dependencies: PyYAML, Rich, Flask, RunPod SDK, Paramiko (SSH), and dev tools (pytest, ruff, mypy).

## 3. Configure API Keys

Set the required environment variables:

```bash
# RunPod — required for experiment execution
export RUNPOD_API_KEY="your-runpod-api-key"

# Anthropic — required for Claude Code agent runtime
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

You can add these to your shell profile (`~/.zshrc`, `~/.bashrc`) or use a `.env` file with your preferred env loader.

To get your RunPod API key:
1. Log in to https://runpod.io
2. Go to Settings > API Keys
3. Create a new key with full access

## 4. Configure the Project

```bash
# Copy the example config
cp config.example.yaml config.yaml
```

Edit `config.yaml` to match your setup. Key settings to review:

```yaml
# GPU type — choose based on your RunPod budget and needs
runpod_gpu_type: "NVIDIA A100 80GB PCIe"

# Maximum concurrent pods — controls parallelism and cost
runpod_max_pods: 4

# Use spot instances for lower cost (may be preempted)
runpod_spot: true

# Research focus: 1=explore many ideas, 3=balanced, 5=deep focus on one idea
research_focus: 3

# Writing mode: parallel (faster), sequential (more coherent), codex (uses Codex)
writing_mode: parallel
```

If you have a RunPod network volume for persistent storage, set `runpod_volume_id`.

## 5. Configure MCP Servers (Optional)

For enhanced literature search, configure the arXiv MCP server in your Claude Code settings.

Add to your Claude Code MCP configuration (typically in `~/.claude/settings.json` or project `.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "uvx",
      "args": ["mcp-arxiv"]
    }
  }
}
```

Install the arXiv MCP server if not already available:

```bash
# Using uvx (recommended)
uvx mcp-arxiv

# Or install globally
pip install mcp-arxiv
```

This gives agents direct access to arXiv search and paper retrieval during the literature search stage.

## 6. Initialize Your First Workspace

```bash
# Initialize a research project
tao init "Improving few-shot learning with retrieval-augmented prompting"
```

This creates a workspace directory under `workspaces/` containing:
- `topic.txt` -- Your research topic
- `config.yaml` -- Project configuration (copied from your config)
- `.tao/system.json` -- Pipeline state (stage, iteration, scores)
- Directory structure for ideas, experiments, writing, and logs

Verify the workspace was created:

```bash
tao status workspaces/improving_fewshot_*
```

## 7. Launch the Pipeline

Start a Claude Code session in the workspace directory and use the plugin commands:

```bash
cd workspaces/improving_fewshot_*

# Start Claude Code
claude

# Inside Claude Code, use plugin commands:
# /start           -- Begin the pipeline
# /status          -- Check current stage and progress
# /continue        -- Resume if paused
```

The pipeline will autonomously:
1. Search arXiv for related work
2. Run a multi-agent debate to generate research ideas
3. Plan and execute experiments on RunPod GPUs
4. Analyze results with statistical tests
5. Write the paper section by section
6. Compile LaTeX to PDF
7. Run simulated peer review
8. Reflect and evolve for the next project

## Monitoring

While the pipeline runs, use these tools to monitor progress:

```bash
# CLI monitoring (from another terminal)
tao status ./
tao experiment-status ./
tao dashboard ./

# Check experiment logs
ls logs/
cat logs/experiment_records.jsonl
```

## Troubleshooting

### RunPod pods fail to start
- Check your API key: `echo $RUNPOD_API_KEY`
- Verify GPU availability on RunPod dashboard
- Try a different `runpod_gpu_type` or set `runpod_cloud_type: "ALL"`

### Pipeline stalls at a stage
- Run `tao self-heal-scan .` to check for fixable errors
- Use `/debug` in Claude Code to diagnose
- Check `logs/errors.jsonl` for error details

### LaTeX compilation fails
- Ensure `pdflatex` is installed: `which pdflatex`
- macOS: `brew install --cask mactex-no-gui`
- Ubuntu: `sudo apt-get install texlive-latex-extra`

### Out of RunPod credits
- The system will pause experiment stages
- Resume with `/continue` after adding credits
