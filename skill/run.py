"""Portable helper entrypoint for the DeepResearch skill."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tao.orchestrate import (  # noqa: E402
    cli_evolve,
    cli_init,
    cli_init_from_spec,
    cli_next,
    cli_record,
    cli_status,
    render_skill_prompt,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DeepResearch skill helper: portable entrypoint for Tao workspaces",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new workspace")
    init_group = init_parser.add_mutually_exclusive_group(required=True)
    init_group.add_argument("--topic", help="Research topic")
    init_group.add_argument("--spec-file", help="Path to a spec.md file")
    init_parser.add_argument("--config", default="", help="Optional config YAML path")
    init_parser.add_argument(
        "--workspace-dir",
        default="",
        help="Optional parent directory for new workspaces",
    )

    status_parser = subparsers.add_parser("status", help="Show workspace status")
    status_parser.add_argument("--workspace", default=".", help="Workspace path")

    next_parser = subparsers.add_parser("next", help="Show the next orchestrator action")
    next_parser.add_argument("--workspace", default=".", help="Workspace path")

    record_parser = subparsers.add_parser("record", help="Record a stage result")
    record_parser.add_argument("--workspace", default=".", help="Workspace path")
    record_parser.add_argument("--stage", required=True, help="Pipeline stage name")
    record_parser.add_argument("--result", required=True, help="Result summary")
    record_parser.add_argument("--score", type=float, default=0.0, help="Numeric score")

    prompt_parser = subparsers.add_parser(
        "render-prompt",
        help="Render a Tao role prompt for the given workspace and skill",
    )
    prompt_parser.add_argument("--workspace", default=".", help="Workspace path")
    prompt_parser.add_argument("--skill", required=True, help="Skill name, e.g. planner")

    evolve_parser = subparsers.add_parser(
        "evolve",
        help="Show or reset evolution log state",
    )
    evolve_parser.add_argument("--workspace", default=".", help="Workspace path")
    evolve_parser.add_argument(
        "--mode",
        default="show",
        choices=["show", "apply", "reset"],
        help="Evolution operation",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "init":
        if args.spec_file:
            print(cli_init_from_spec(args.spec_file, args.config, args.workspace_dir))
        else:
            print(cli_init(args.topic, args.config, args.workspace_dir))
        return

    if args.command == "status":
        print(cli_status(args.workspace))
        return

    if args.command == "next":
        print(cli_next(args.workspace))
        return

    if args.command == "record":
        print(cli_record(args.workspace, args.stage, args.result, args.score))
        return

    if args.command == "render-prompt":
        print(render_skill_prompt(args.workspace, args.skill))
        return

    if args.command == "evolve":
        print(cli_evolve(f"{args.workspace} --{args.mode}".strip()))
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
