"""CLI entry point for the Sibyl Research System."""
from __future__ import annotations
import json
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    app = typer.Typer(name="sibyl", help="Sibyl Research System — Autonomous AI Scientist")
    console = Console()
    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False


def main():
    """Main CLI entry point."""
    if not HAS_TYPER:
        _fallback_main()
        return

    @app.command()
    def status(workspace: str = typer.Argument(".", help="Workspace path")):
        """Show pipeline status."""
        from sibyl.orchestrate import cli_status
        result = cli_status(workspace)
        data = json.loads(result)

        table = Table(title="Pipeline Status")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        for key, val in data.items():
            if key != "errors":
                table.add_row(key, str(val))
        console.print(table)

    @app.command(name="experiment-status")
    def experiment_status(workspace: str = typer.Argument(".", help="Workspace path")):
        """Show experiment progress."""
        from sibyl.gpu_scheduler import get_progress_summary
        summary = get_progress_summary(workspace)

        table = Table(title="Experiment Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        for key, val in summary.items():
            if isinstance(val, (int, float)):
                table.add_row(key, str(val))
        console.print(table)

    @app.command()
    def dispatch(workspace: str = typer.Argument(".", help="Workspace path")):
        """Dispatch next batch of experiment tasks."""
        from sibyl.gpu_scheduler import get_next_batch
        batch = get_next_batch(workspace, list(range(8)))  # assume up to 8 GPUs
        if not batch:
            console.print("[yellow]No tasks ready to dispatch[/yellow]")
        else:
            for assignment in batch:
                console.print(f"  Task: {assignment['task_id']} \u2192 GPUs: {assignment['gpu_ids']}")

    @app.command()
    def evolve(
        workspace: str = typer.Argument(".", help="Workspace path"),
        show: bool = typer.Option(False, help="Show evolution log"),
        reset: bool = typer.Option(False, help="Reset evolution history"),
    ):
        """Manage system self-evolution."""
        from sibyl.evolution import load_evolution_log
        if show:
            log = load_evolution_log(workspace)
            for entry in log[-10:]:
                console.print(f"  [{entry.get('quality_trajectory', 'unknown')}] {entry.get('issues_count', 0)} issues")
        elif reset:
            log_file = Path(workspace) / "logs" / "evolution_log.jsonl"
            if log_file.exists():
                log_file.unlink()
            console.print("[green]Evolution history reset[/green]")

    @app.command(name="self-heal-scan")
    def self_heal_scan(workspace: str = typer.Argument(".", help="Workspace path")):
        """Scan for fixable errors."""
        from sibyl.self_heal import SelfHealRouter
        router = SelfHealRouter(workspace)
        errors = router.scan_errors()
        if not errors:
            console.print("[green]No actionable errors found[/green]")
        else:
            for err in errors:
                console.print(f"  [{err['category']}] {err['message'][:80]} (attempts: {err['attempts']})")

    @app.command(name="latex-compile")
    def latex_compile(workspace: str = typer.Argument(".", help="Workspace path")):
        """Compile LaTeX to PDF."""
        from sibyl.latex_pipeline import compile_pdf
        result = compile_pdf(workspace)
        if result["success"]:
            console.print(f"[green]PDF generated: {result['pdf_path']}[/green]")
        else:
            console.print(f"[red]LaTeX compilation failed: {result['log'][:200]}[/red]")

    @app.command()
    def init(
        topic: str = typer.Argument(..., help="Research topic or spec.md path"),
        config: str = typer.Option("", help="Config YAML path"),
    ):
        """Initialize a new research project."""
        from sibyl.orchestrate import cli_init, cli_init_from_spec
        if topic.endswith(".md") and Path(topic).exists():
            path = cli_init_from_spec(topic, config)
        else:
            path = cli_init(topic, config)
        console.print(f"[green]Workspace created: {path}[/green]")

    @app.command()
    def dashboard(workspace: str = typer.Argument(".", help="Workspace path")):
        """Show JSON dashboard data."""
        from sibyl.orchestrate import cli_status
        from sibyl.gpu_scheduler import get_progress_summary
        from sibyl.experiment_recovery import get_experiment_summary

        status = json.loads(cli_status(workspace))
        progress = get_progress_summary(workspace)
        experiments = get_experiment_summary(workspace)

        data = {
            "status": status,
            "experiment_progress": progress,
            "experiment_state": experiments,
        }
        console.print_json(json.dumps(data, indent=2))

    app()


def _fallback_main():
    """Fallback CLI without typer."""
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print("Sibyl Research System CLI")
        print("Commands: status, init, experiment-status, dispatch, evolve, self-heal-scan, latex-compile, dashboard")
        print("Install typer and rich for full CLI: pip install typer rich")
        return

    cmd = args[0]
    workspace = args[1] if len(args) > 1 else "."

    if cmd == "status":
        from sibyl.orchestrate import cli_status
        print(cli_status(workspace))
    elif cmd == "init":
        from sibyl.orchestrate import cli_init
        topic = args[1] if len(args) > 1 else "research"
        print(cli_init(topic))
    elif cmd == "experiment-status":
        from sibyl.gpu_scheduler import get_progress_summary
        print(json.dumps(get_progress_summary(workspace), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
