"""Command line interface for the initial ModForge workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modforge import __version__
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject
from modforge.reports.markdown import render_deployment_report

DEFAULT_PROJECT_FILE = Path("modforge.project.json")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modforge")
    parser.add_argument("--version", action="version", version=f"modforge {__version__}")
    subcommands = parser.add_subparsers(required=True)

    project = subcommands.add_parser("project", help="Manage project files")
    project_subcommands = project.add_subparsers(required=True)
    init = project_subcommands.add_parser("init", help="Create a project file")
    init.add_argument("--name", required=True)
    init.add_argument("--game-root", required=True, type=Path)
    init.add_argument("--mods-dir", required=True, type=Path)
    init.add_argument("--staging-dir", type=Path, default=Path(".modforge/staging"))
    init.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    init.set_defaults(handler=handle_project_init)

    scan = subcommands.add_parser("scan-mods", help="Scan the configured mods directory")
    scan.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    scan.add_argument("--json", action="store_true", help="Print JSON output")
    scan.set_defaults(handler=handle_scan_mods)

    plan = subcommands.add_parser("plan", help="Create a dry-run deployment plan")
    plan.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    plan.add_argument("--json", action="store_true", help="Print JSON output")
    plan.set_defaults(handler=handle_plan)

    report = subcommands.add_parser("report", help="Write a Markdown deployment report")
    report.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    report.add_argument("--output", type=Path, default=Path(".modforge/conflict-report.md"))
    report.set_defaults(handler=handle_report)

    return parser


def handle_project_init(args: argparse.Namespace) -> int:
    project = ModProject.create(
        name=args.name,
        game_root=args.game_root,
        mods_dir=args.mods_dir,
        staging_dir=args.staging_dir,
    )
    project.save(args.project_file)
    print(f"Created {args.project_file}")
    return 0


def handle_scan_mods(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    packages = scan_mods(project.mods_dir)
    payload = [package.to_dict() for package in packages]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for package in packages:
            print(f"{package.priority:03d} {'on ' if package.enabled else 'off'} {package.name}")
    return 0


def handle_plan(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    plan = build_deployment_plan(project, scan_mods(project.mods_dir))
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        print(f"Operations: {len(plan.operations)}")
        print(f"Conflicts: {len(plan.conflicts)}")
        for conflict in plan.conflicts:
            print(f"- {conflict.destination_path}: winner={conflict.winning_mod}")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    plan = build_deployment_plan(project, scan_mods(project.mods_dir))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_deployment_report(project, plan), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
