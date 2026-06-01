"""Command line interface for the initial ModForge workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modforge import __version__
from modforge.core.deployer import apply_to_game, apply_to_staging, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.game_profile import builtin_profiles
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject
from modforge.reports.markdown import render_deployment_report
from modforge.tools.checker import check_tools
from modforge.translation.exporter import extract_strings, write_entries_csv

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
    init.add_argument("--profile", default="generic-folder", help="Built-in game profile id")
    init.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    init.set_defaults(handler=handle_project_init)

    profiles = subcommands.add_parser("profiles", help="List built-in game profiles")
    profiles.add_argument("--json", action="store_true")
    profiles.set_defaults(handler=handle_profiles)

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

    profile = subcommands.add_parser("profile", help="Manage enabled mods and priorities")
    profile_subcommands = profile.add_subparsers(required=True)
    profile_list = profile_subcommands.add_parser("list", help="List user mod-set profiles")
    profile_list.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_list.add_argument("--json", action="store_true")
    profile_list.set_defaults(handler=handle_profile_list)

    profile_show = profile_subcommands.add_parser("show", help="Show active profile")
    profile_show.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_show.add_argument("--json", action="store_true")
    profile_show.set_defaults(handler=handle_profile_show)

    profile_create = profile_subcommands.add_parser("create", help="Create a user mod-set profile")
    profile_create.add_argument("profile_id")
    profile_create.add_argument("--name")
    profile_create.add_argument("--copy-from")
    profile_create.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_create.set_defaults(handler=handle_profile_create)

    profile_switch = profile_subcommands.add_parser("switch", help="Switch the active user profile")
    profile_switch.add_argument("profile_id")
    profile_switch.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_switch.set_defaults(handler=handle_profile_switch)

    profile_delete = profile_subcommands.add_parser("delete", help="Delete a user mod-set profile")
    profile_delete.add_argument("profile_id")
    profile_delete.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_delete.set_defaults(handler=handle_profile_delete)

    profile_enable = profile_subcommands.add_parser("enable", help="Enable a mod id")
    profile_enable.add_argument("mod_id")
    profile_enable.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_enable.set_defaults(handler=handle_profile_enable)

    profile_disable = profile_subcommands.add_parser("disable", help="Disable a mod id")
    profile_disable.add_argument("mod_id")
    profile_disable.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_disable.set_defaults(handler=handle_profile_disable)

    profile_priority = profile_subcommands.add_parser(
        "set-priority",
        help="Set mod priority order from low to high priority",
    )
    profile_priority.add_argument("mod_ids", nargs="+")
    profile_priority.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    profile_priority.set_defaults(handler=handle_profile_set_priority)

    tools = subcommands.add_parser("tools", help="Manage external tool paths")
    tools_subcommands = tools.add_subparsers(required=True)
    tools_check = tools_subcommands.add_parser("check", help="Check configured external tools")
    tools_check.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    tools_check.add_argument("--json", action="store_true")
    tools_check.set_defaults(handler=handle_tools_check)

    tools_set = tools_subcommands.add_parser("set", help="Set one external tool path")
    tools_set.add_argument("tool_id")
    tools_set.add_argument("path")
    tools_set.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    tools_set.set_defaults(handler=handle_tools_set)

    apply = subcommands.add_parser("apply-staging", help="Copy winning files into staging")
    apply.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    apply.add_argument("--yes", action="store_true", help="Confirm staging write")
    apply.add_argument("--json", action="store_true")
    apply.set_defaults(handler=handle_apply_staging)

    apply_game = subcommands.add_parser("apply-game", help="Copy winning files into game root")
    apply_game.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    apply_game.add_argument("--yes", action="store_true", help="Confirm game-root write")
    apply_game.add_argument("--json", action="store_true")
    apply_game.set_defaults(handler=handle_apply_game)

    restore = subcommands.add_parser("restore", help="Restore a game apply manifest")
    restore.add_argument("--manifest", required=True, type=Path)
    restore.add_argument("--yes", action="store_true", help="Confirm restore write")
    restore.add_argument("--json", action="store_true")
    restore.set_defaults(handler=handle_restore)

    translation = subcommands.add_parser("translation", help="Translation workspace helpers")
    translation_subcommands = translation.add_subparsers(required=True)
    translation_extract = translation_subcommands.add_parser(
        "extract",
        help="Extract strings from JSON/CSV/TXT files",
    )
    translation_extract.add_argument("--source", required=True, type=Path)
    translation_extract.add_argument("--output", required=True, type=Path)
    translation_extract.add_argument("--json", action="store_true")
    translation_extract.set_defaults(handler=handle_translation_extract)

    return parser


def handle_project_init(args: argparse.Namespace) -> int:
    project_dir = args.project_file.resolve(strict=False).parent
    staging_dir = args.staging_dir if args.staging_dir.is_absolute() else project_dir / args.staging_dir
    project = ModProject.create(
        name=args.name,
        game_root=args.game_root,
        mods_dir=args.mods_dir,
        staging_dir=staging_dir,
        game_profile=args.profile,
    )
    project.save(args.project_file)
    print(f"Created {args.project_file}")
    return 0


def handle_profiles(args: argparse.Namespace) -> int:
    profiles = builtin_profiles()
    if args.json:
        print(json.dumps([profile.to_dict() for profile in profiles], indent=2))
    else:
        for profile in profiles:
            print(f"{profile.id:16} {profile.display_name}")
    return 0


def handle_scan_mods(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    packages = scan_mods(project.mods_dir, project.active_profile())
    payload = [package.to_dict() for package in packages]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for package in packages:
            print(f"{package.priority:03d} {'on ' if package.enabled else 'off'} {package.name}")
    return 0


def handle_plan(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    plan = build_deployment_plan(project, scan_mods(project.mods_dir, project.active_profile()))
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
    plan = build_deployment_plan(project, scan_mods(project.mods_dir, project.active_profile()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_deployment_report(project, plan), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def handle_profile_list(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    payload = [profile.to_dict() for profile in project.user_profiles]
    if args.json:
        print(json.dumps({"active_user_profile": project.active_user_profile, "profiles": payload}, indent=2))
    else:
        for profile in project.user_profiles:
            marker = "*" if profile.id == project.active_user_profile else " "
            print(f"{marker} {profile.id:16} {profile.name}")
    return 0


def handle_profile_show(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    profile = project.active_profile()
    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        print(f"Active profile: {profile.name} ({profile.id})")
        print(f"Disabled mods: {', '.join(profile.disabled_mod_ids) or '-'}")
        print(f"Priority order: {', '.join(profile.mod_priority_order) or '-'}")
    return 0


def handle_profile_create(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    profile = project.create_user_profile(args.profile_id, name=args.name, copy_from=args.copy_from)
    project.save(args.project_file)
    copied = f" from {args.copy_from}" if args.copy_from else ""
    print(f"Created profile {profile.id}{copied}")
    return 0


def handle_profile_switch(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    profile = project.switch_user_profile(args.profile_id)
    project.save(args.project_file)
    print(f"Switched to profile {profile.id}")
    return 0


def handle_profile_delete(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    profile = project.delete_user_profile(args.profile_id)
    project.save(args.project_file)
    print(f"Deleted profile {profile.id}")
    return 0


def handle_profile_enable(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    project.set_mod_enabled(args.mod_id, True)
    project.save(args.project_file)
    print(f"Enabled {args.mod_id}")
    return 0


def handle_profile_disable(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    project.set_mod_enabled(args.mod_id, False)
    project.save(args.project_file)
    print(f"Disabled {args.mod_id}")
    return 0


def handle_profile_set_priority(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    project.set_priority_order(args.mod_ids)
    project.save(args.project_file)
    print("Updated priority order")
    return 0


def handle_tools_check(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    checks = check_tools(project.external_tools)
    if args.json:
        print(json.dumps([check.to_dict() for check in checks], indent=2))
    else:
        for check in checks:
            state = "ok" if check.exists else "missing"
            print(f"{state:7} {check.tool_id}: {check.path or check.warning}")
    return 0


def handle_tools_set(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    project.set_tool_path(args.tool_id, args.path)
    project.save(args.project_file)
    print(f"Set {args.tool_id}")
    return 0


def handle_apply_staging(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to write staging without --yes. Run `modforge plan` first.")
        return 2

    project = ModProject.load(args.project_file)
    packages = scan_mods(project.mods_dir, project.active_profile())
    plan = build_deployment_plan(project, packages)
    manifest = apply_to_staging(project, plan, packages)
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2))
    else:
        print(f"Applied to staging: {project.staging_dir}")
        print(f"Copied: {len(manifest.copied_files)}")
        print(f"Overwritten: {len(manifest.overwritten_files)}")
        print(f"Skipped: {len(manifest.skipped_files)}")
    return 0


def handle_apply_game(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to write the game root without --yes. Run `modforge plan` first.")
        return 2

    project = ModProject.load(args.project_file)
    packages = scan_mods(project.mods_dir, project.active_profile())
    plan = build_deployment_plan(project, packages)
    manifest = apply_to_game(project, plan, packages)
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2))
    else:
        print(f"Applied to game root: {project.game_root}")
        print(f"Manifest id: {manifest.manifest_id}")
        print(f"Copied: {len(manifest.copied_files)}")
        print(f"Overwritten: {len(manifest.overwritten_files)}")
        print(f"Skipped: {len(manifest.skipped_files)}")
        print(f"Backups: {len(manifest.backups)}")
    return 0


def handle_restore(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to restore without --yes.")
        return 2

    manifest = restore_manifest(args.manifest)
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2))
    else:
        print(f"Restored manifest: {manifest.manifest_id}")
        print(f"Target root: {manifest.target_root}")
    return 0


def handle_translation_extract(args: argparse.Namespace) -> int:
    entries = extract_strings(args.source)
    write_entries_csv(entries, args.output)
    if args.json:
        print(json.dumps({"entries": len(entries), "output": str(args.output)}, indent=2))
    else:
        print(f"Extracted {len(entries)} strings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
