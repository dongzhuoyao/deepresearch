"""CLI entry point for the Tao Research System."""
from __future__ import annotations
import json
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    app = typer.Typer(name="tao", help="Tao Research System — Autonomous AI Scientist")
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
        from tao.orchestrate import cli_status
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
        from tao.gpu_scheduler import get_progress_summary
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
        from tao.gpu_scheduler import get_next_batch
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
        from tao.evolution import load_evolution_log
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
        from tao.self_heal import SelfHealRouter
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
        from tao.latex_pipeline import compile_pdf
        result = compile_pdf(workspace)
        if result["success"]:
            console.print(f"[green]PDF generated: {result['pdf_path']}[/green]")
        else:
            console.print(f"[red]LaTeX compilation failed: {result['log'][:200]}[/red]")

    @app.command(name="cli-record")
    def cli_record_cmd(
        workspace: str = typer.Argument(..., help="Workspace path"),
        stage: str = typer.Argument(..., help="Pipeline stage name"),
        result: str = typer.Argument(..., help="Result summary text"),
        score: float = typer.Argument(0.0, help="Numeric score (0-10)"),
    ):
        """Record stage result and advance pipeline."""
        from tao.orchestrate import cli_record
        next_stage = cli_record(workspace, stage, result, score)
        console.print(f"[green]Recorded {stage} → next: {next_stage}[/green]")

    @app.command()
    def init(
        topic: str = typer.Argument(..., help="Research topic or spec.md path"),
        config: str = typer.Option("", help="Config YAML path"),
    ):
        """Initialize a new research project."""
        from tao.orchestrate import cli_init, cli_init_from_spec
        if topic.endswith(".md") and Path(topic).exists():
            path = cli_init_from_spec(topic, config)
        else:
            path = cli_init(topic, config)
        console.print(f"[green]Workspace created: {path}[/green]")

    @app.command()
    def dashboard(workspace: str = typer.Argument(".", help="Workspace path")):
        """Show JSON dashboard data."""
        from tao.orchestrate import cli_status
        from tao.gpu_scheduler import get_progress_summary
        from tao.experiment_recovery import get_experiment_summary

        status = json.loads(cli_status(workspace))
        progress = get_progress_summary(workspace)
        experiments = get_experiment_summary(workspace)

        data = {
            "status": status,
            "experiment_progress": progress,
            "experiment_state": experiments,
        }
        console.print_json(json.dumps(data, indent=2))

    @app.command()
    def webui(
        workspaces: str = typer.Option("workspaces", help="Workspaces directory"),
        host: str = typer.Option("127.0.0.1", help="Bind host"),
        port: int = typer.Option(3000, help="Port (default 3000, try 3001/3002 if busy)"),
    ):
        """Start the web dashboard UI."""
        from tao.webui.app import create_webui_app
        app_ = create_webui_app(workspaces)
        console.print(f"[green]WebUI starting at http://{host}:{port}[/green]")
        app_.run(host=host, port=port)

    @app.command(name="serve")
    def serve(
        workspaces: str = typer.Option("workspaces", help="Workspaces directory"),
        host: str = typer.Option("127.0.0.1", help="Bind host"),
        port: int = typer.Option(3000, help="Port (default 3000)"),
    ):
        """Start the API-only dashboard server."""
        from tao.dashboard.server import run_dashboard
        console.print(f"[green]Dashboard API starting at http://{host}:{port}[/green]")
        run_dashboard(workspaces, port)

    app()


def _fallback_main():
    """Fallback CLI without typer."""
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print("Tao Research System CLI")
        print("Commands: status, init, cli-record, experiment-status, dispatch, evolve, self-heal-scan, latex-compile, dashboard")
        print("Install typer and rich for full CLI: pip install typer rich")
        return

    cmd = args[0]
    workspace = args[1] if len(args) > 1 else "."

    if cmd == "status":
        from tao.orchestrate import cli_status
        print(cli_status(workspace))
    elif cmd == "init":
        from tao.orchestrate import cli_init
        topic = args[1] if len(args) > 1 else "research"
        print(cli_init(topic))
    elif cmd == "cli-record":
        from tao.orchestrate import cli_record
        stage = args[2] if len(args) > 2 else ""
        result = args[3] if len(args) > 3 else ""
        score = float(args[4]) if len(args) > 4 else 0.0
        next_stage = cli_record(workspace, stage, result, score)
        print(f"Recorded {stage} → next: {next_stage}")
    elif cmd == "experiment-status":
        from tao.gpu_scheduler import get_progress_summary
        print(json.dumps(get_progress_summary(workspace), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
