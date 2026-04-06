"""Action dispatcher — converts Actions to execution scripts."""
from __future__ import annotations
from tao.orchestration.models import Action


def render_execution_script(action: Action) -> str:
    """Convert an Action to a deterministic execution script.

    The script tells Claude Code exactly what to do, saving tokens
    and enabling auditing.
    """
    renderers = {
        "skill": _script_skill,
        "skills_parallel": _script_skills_parallel,
        "team": _script_team,
        "bash": _script_bash,
        "gpu_poll": _script_gpu_poll,
        "experiment_wait": _script_experiment_wait,
        "agents_parallel": _script_agents_parallel,
        "done": _script_done,
    }
    renderer = renderers.get(action.action_type, _script_done)
    script = renderer(action)
    action.execution_script = script
    return script


def _script_skill(action: Action) -> str:
    if not action.skills:
        return "# No skills specified"
    skill = action.skills[0]
    name = skill.get("name", "unknown")
    desc = skill.get("description", "")
    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        f"# Action: invoke skill '{name}'",
        f"# Description: {desc}",
        f"# Estimated: {action.estimated_minutes} minutes",
        "",
        f"Step 1: Invoke the '{name}' skill",
        f"  - Use Agent tool with subagent_type appropriate for '{name}'",
        f"  - Task: {desc}",
        f"  - Workspace: provide workspace path",
        "",
        f"Step 2: Record result",
        f"  - Run: tao cli-record . {action.stage} '<result_summary>' <score>",
    ]
    return "\n".join(lines)


def _script_skills_parallel(action: Action) -> str:
    if not action.agents:
        return "# No agents specified for parallel execution"
    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        f"# Action: run {len(action.agents)} agents in parallel",
        "",
        "Step 1: Launch all agents in parallel (single message with multiple Agent tool calls):",
    ]
    for i, agent in enumerate(action.agents, 1):
        name = agent.get("name", "unknown")
        desc = agent.get("description", "")
        lines.append(f"  Agent {i}: '{name}' — {desc}")
    lines.extend([
        "",
        "Step 2: Wait for all agents to complete",
        "",
        f"Step 3: Record result",
        f"  - Run: tao cli-record . {action.stage} '<combined_summary>' <score>",
    ])
    return "\n".join(lines)


def _script_team(action: Action) -> str:
    if not action.team:
        return "# No team specified"
    team = action.team
    team_name = team.get("name", "team")
    prompt = team.get("prompt", "")
    agents = team.get("agents", [])
    post_steps = team.get("post_steps", [])

    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        f"# Action: multi-agent team '{team_name}'",
        f"# Team prompt: {prompt}",
        "",
        f"Step 1: Launch team '{team_name}' with {len(agents)} agents in parallel:",
    ]
    for i, agent in enumerate(agents, 1):
        name = agent.get("name", "unknown")
        desc = agent.get("description", "")
        lines.append(f"  Agent {i}: '{name}' — {desc}")
    lines.append("")
    lines.append("Step 2: Wait for all agents to complete their perspectives")

    if post_steps:
        lines.append("")
        lines.append("Step 3: Post-processing:")
        for i, step in enumerate(post_steps, 1):
            name = step.get("skill", "unknown")
            desc = step.get("description", "")
            lines.append(f"  {i}. Invoke '{name}' — {desc}")

    lines.extend([
        "",
        f"Step {4 if post_steps else 3}: Record result",
        f"  - Run: tao cli-record . {action.stage} '<summary>' <score>",
    ])
    return "\n".join(lines)


def _script_bash(action: Action) -> str:
    cmd = action.bash_command or "echo 'No command'"
    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        f"# Action: execute bash command",
        "",
        f"Step 1: Run command:",
        f"  {cmd}",
        "",
        "Step 2: Check exit code and capture output",
        "",
        f"Step 3: Record result",
        f"  - Run: tao cli-record . {action.stage} '<output_summary>' <score>",
    ]
    return "\n".join(lines)


def _script_gpu_poll(action: Action) -> str:
    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        "# Action: poll for free GPUs on RunPod",
        "",
        "Step 1: Generate and execute GPU poll script",
        "  - Script checks nvidia-smi for free GPUs",
        "  - Writes GPU IDs to marker file when found",
        "",
        "Step 2: When GPUs found, dispatch experiment tasks",
        "",
        f"Step 3: Record result",
        f"  - Run: tao cli-record . {action.stage} 'GPUs acquired' 0",
    ]
    return "\n".join(lines)


def _script_experiment_wait(action: Action) -> str:
    monitor = action.experiment_monitor or {}
    timeout = monitor.get("timeout_minutes", 120)
    lines = [
        f"# Stage: {action.stage} (iteration {action.iteration})",
        f"# Action: monitor running experiments (timeout: {timeout}m)",
        "",
        "Step 1: Start experiment monitor daemon",
        "  - Monitor checks task DONE markers and PID files",
        "  - Reports progress via heartbeat",
        "",
        "Step 2: Wait for all tasks to complete or timeout",
        "",
        "Step 3: Collect results from RunPod pod",
        "",
        f"Step 4: Record result",
        f"  - Run: tao cli-record . {action.stage} '<results_summary>' <score>",
    ]
    return "\n".join(lines)


def _script_agents_parallel(action: Action) -> str:
    return _script_skills_parallel(action)


def _script_done(action: Action) -> str:
    return f"# Pipeline stage '{action.stage}' complete. No further action needed."
