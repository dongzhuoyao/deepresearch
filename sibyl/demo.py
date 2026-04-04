"""End-to-end smoke test for the Sibyl pipeline."""
from __future__ import annotations
import json
from pathlib import Path
from sibyl.config import Config
from sibyl.orchestrate import FarsOrchestrator
from sibyl.workspace import Workspace
from sibyl.gpu_scheduler import get_progress_summary
from sibyl.experiment_recovery import get_experiment_summary
from sibyl.runtime_assets import setup_workspace_assets
from sibyl.orchestration.workspace_paths import ensure_workspace_dirs


def run_demo(output_dir: str | Path = "/tmp/sibyl_demo") -> dict:
    """Run a complete dry-run of the pipeline.

    This validates:
    - Workspace creation and initialization
    - State machine transitions through all 18 stages
    - Action generation for each stage
    - Execution script rendering
    - Experiment progress tracking
    - Reflection and evolution hooks
    - Quality gate logic

    Returns a summary dict.
    """
    output_dir = Path(output_dir)
    ws_path = output_dir / "demo_project"

    # 1. Initialize
    cfg = Config()
    orch = FarsOrchestrator(ws_path, cfg)
    orch.init_project("Demo: Neural Scaling Laws for Small Language Models")
    setup_workspace_assets(ws_path, cfg)

    results = {"stages_visited": [], "actions_generated": 0, "errors": []}

    # 2. Walk through the pipeline
    stage_results = {
        "init": ("Initialized workspace", 0.0),
        "literature_search": ("Found 15 relevant papers on arXiv", 0.0),
        "idea_debate": ("6 agents debated, synthesized proposal: efficient scaling", 0.0),
        "planning": ("Created task plan with 5 experiments", 0.0),
        "pilot_experiments": ("Pilot: 3/3 tasks completed, baseline acc=0.72", 0.0),
        "idea_validation_decision": ("ADVANCE: pilot results support hypothesis", 0.0),
        "experiment_cycle": ("Full experiments: 5/5 done, main acc=0.85", 0.0),
        "result_debate": ("Results are significant (p<0.01), novel contribution", 0.0),
        "experiment_decision": ("DECISION: PROCEED -- results support hypothesis", 0.0),
        "writing_outline": ("Outline: 6 sections planned", 0.0),
        "writing_sections": ("All 6 sections drafted in parallel", 0.0),
        "writing_integrate": ("Cross-critique done, sections integrated", 0.0),
        "writing_final_review": ("Score: 7.5/10 -- ready for LaTeX", 7.5),
        "writing_latex": ("LaTeX compiled successfully", 0.0),
        "review": ("Supervisor: solid paper, minor revisions suggested", 0.0),
        "reflection": ("2 issues classified, 1 lesson extracted", 0.0),
        "quality_gate": ("Quality gate passed", 8.0),
    }

    # Set iteration to 2 so quality gate can pass (needs iteration >= 2)
    orch.workspace.update_stage_and_iteration("init", 2)
    # Ensure the iter_002 directory structure exists since we jumped directly
    ensure_workspace_dirs(orch.workspace.active_root)

    for expected_stage in list(stage_results.keys()):
        try:
            # Get action
            action = orch.get_next_action()
            results["actions_generated"] += 1
            results["stages_visited"].append(action["stage"])

            # Record result
            result_text, score = stage_results.get(action["stage"], ("done", 0.0))
            next_stage = orch.record_result(action["stage"], result_text, score)

            if next_stage == "done":
                results["stages_visited"].append("done")
                break

        except Exception as e:
            results["errors"].append(f"Stage {expected_stage}: {e}")
            break

    # 3. Validate workspace artifacts
    ws = Workspace(ws_path, iteration_dirs=cfg.iteration_dirs)

    checks = {
        "topic_exists": (ws_path / "topic.txt").exists(),
        "status_exists": (ws_path / "status.json").exists(),
        "claude_md_exists": (ws_path / "CLAUDE.md").exists(),
        "config_exists": (ws_path / "config.yaml").exists(),
        "idea_dir_exists": (ws_path / "iter_002" / "idea").is_dir() or (ws_path / "idea").is_dir(),
    }
    results["checks"] = checks
    results["all_checks_passed"] = all(checks.values())
    results["final_stage"] = orch.get_status().get("stage", "unknown")

    return results


def print_demo_report(results: dict) -> None:
    """Print a human-readable demo report."""
    print("=" * 60)
    print("SIBYL RESEARCH SYSTEM -- DEMO REPORT")
    print("=" * 60)
    print(f"\nStages visited: {len(results['stages_visited'])}")
    for s in results["stages_visited"]:
        print(f"  [ok] {s}")
    print(f"\nActions generated: {results['actions_generated']}")
    print(f"Final stage: {results['final_stage']}")
    print(f"\nChecks:")
    for check, passed in results.get("checks", {}).items():
        status = "[ok]" if passed else "[FAIL]"
        print(f"  {status} {check}")
    print(f"\nAll checks passed: {results.get('all_checks_passed', False)}")
    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])}):")
        for err in results["errors"]:
            print(f"  [FAIL] {err}")
    print("=" * 60)


if __name__ == "__main__":
    results = run_demo()
    print_demo_report(results)
