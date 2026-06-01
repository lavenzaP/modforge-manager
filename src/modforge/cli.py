"""Command line interface for the initial ModForge workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modforge import __version__
from modforge.core.deployer import apply_to_game, apply_to_staging, preview_restore_manifest, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan, summarize_deployment_plan
from modforge.core.game_profile import (
    builtin_profile,
    builtin_profiles,
    custom_profile_dir,
    import_profile_file,
    load_profile_file,
    preview_profile_dir,
    validate_profile,
)
from modforge.core.manifest_browser import (
    find_manifest,
    latest_manifest_summary,
    list_manifest_summaries,
    summarize_manifest,
)
from modforge.core.mod_package import scan_project_mods
from modforge.core.mod_project import ModProject
from modforge.core.paths import normalize_path
from modforge.core.project_portability import audit_project, export_project, import_project
from modforge.doctor import format_doctor_report, run_doctor
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

    show = project_subcommands.add_parser("show", help="Show project metadata")
    show.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    show.add_argument("--json", action="store_true")
    show.set_defaults(handler=handle_project_show)

    set_paths = project_subcommands.add_parser("set-paths", help="Update project path settings")
    set_paths.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    set_paths.add_argument("--game-root", type=Path)
    set_paths.add_argument("--mods-dir", type=Path)
    set_paths.add_argument("--staging-dir", type=Path)
    set_paths.set_defaults(handler=handle_project_set_paths)

    project_export = project_subcommands.add_parser("export", help="Export project metadata only")
    project_export.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    project_export.add_argument("--out", required=True, type=Path)
    project_export.add_argument("--no-manifests", action="store_true")
    project_export.set_defaults(handler=handle_project_export)

    project_import = project_subcommands.add_parser("import", help="Import a project metadata export")
    project_import.add_argument("export_file", type=Path)
    project_import.add_argument("--target", required=True, type=Path)
    project_import.add_argument("--project-file-name", default="modforge.project.json")
    project_import.set_defaults(handler=handle_project_import)

    project_audit = project_subcommands.add_parser("audit", help="Audit project portability and health")
    project_audit.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    project_audit.add_argument("--json", action="store_true")
    project_audit.set_defaults(handler=handle_project_audit)

    profiles = subcommands.add_parser("profiles", help="List, validate, import, and export game profiles")
    profiles.add_argument("--json", action="store_true")
    profiles.set_defaults(handler=handle_profiles)
    profile_catalog_subcommands = profiles.add_subparsers(dest="profiles_command")

    profiles_validate = profile_catalog_subcommands.add_parser("validate", help="Validate a game profile JSON file")
    profiles_validate.add_argument("profile_file", type=Path)
    profiles_validate.add_argument("--json", action="store_true")
    profiles_validate.set_defaults(handler=handle_profiles_validate)

    profiles_preview = profile_catalog_subcommands.add_parser("preview-map", help="Preview destination mapping for a sample mod")
    profiles_preview.add_argument("profile_file", type=Path)
    profiles_preview.add_argument("sample_mod_dir", type=Path)
    profiles_preview.add_argument("--json", action="store_true")
    profiles_preview.set_defaults(handler=handle_profiles_preview_map)

    profiles_import = profile_catalog_subcommands.add_parser("import", help="Import a custom game profile JSON file")
    profiles_import.add_argument("profile_file", type=Path)
    profiles_import.add_argument("--profile-dir", type=Path)
    profiles_import.add_argument("--force", action="store_true")
    profiles_import.add_argument("--json", action="store_true")
    profiles_import.set_defaults(handler=handle_profiles_import)

    profiles_export = profile_catalog_subcommands.add_parser("export", help="Export a game profile by id")
    profiles_export.add_argument("profile_id")
    profiles_export.add_argument("--out", required=True, type=Path)
    profiles_export.add_argument("--json", action="store_true")
    profiles_export.set_defaults(handler=handle_profiles_export)

    doctor = subcommands.add_parser("doctor", help="Run runtime and project smoke checks")
    doctor.add_argument("--project-file", "--project", type=Path, default=DEFAULT_PROJECT_FILE)
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    doctor.add_argument("--health-report", type=Path, help="Write a Markdown health report")
    doctor.set_defaults(handler=handle_doctor)

    scan = subcommands.add_parser("scan-mods", help="Scan the configured mods directory")
    scan.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    scan.add_argument("--json", action="store_true", help="Print JSON output")
    scan.set_defaults(handler=handle_scan_mods)

    plan = subcommands.add_parser("plan", help="Create a dry-run deployment plan")
    plan.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    plan.add_argument("--json", action="store_true", help="Print JSON output")
    plan.add_argument("--summary", action="store_true", help="Print a compact risk summary")
    plan.set_defaults(handler=handle_plan)

    report = subcommands.add_parser("report", help="Write a Markdown deployment report")
    report.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    report.add_argument("--output", type=Path, default=Path(".modforge/conflict-report.md"))
    report.set_defaults(handler=handle_report)

    manifests = subcommands.add_parser("manifests", help="Inspect game apply manifests")
    manifest_subcommands = manifests.add_subparsers(required=True)
    manifest_list = manifest_subcommands.add_parser("list", help="List project manifests")
    manifest_list.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    manifest_list.add_argument("--json", action="store_true")
    manifest_list.set_defaults(handler=handle_manifests_list)

    manifest_latest = manifest_subcommands.add_parser("latest", help="Show the latest project manifest")
    manifest_latest.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    manifest_latest.add_argument("--json", action="store_true")
    manifest_latest.set_defaults(handler=handle_manifests_latest)

    manifest_show = manifest_subcommands.add_parser("show", help="Show one project manifest")
    manifest_show.add_argument("manifest")
    manifest_show.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    manifest_show.add_argument("--json", action="store_true")
    manifest_show.set_defaults(handler=handle_manifests_show)

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
    restore.add_argument("--project-file", type=Path, default=DEFAULT_PROJECT_FILE)
    restore.add_argument("--manifest", required=True, type=Path)
    restore.add_argument("--path", action="append", dest="paths", help="Restore only this destination path")
    restore.add_argument("--preview", action="store_true", help="Show restore actions without writing files")
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


def handle_project_show(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    if args.json:
        print(json.dumps(project.to_dict(), indent=2))
    else:
        print(f"Project: {project.name}")
        print(f"Game root: {project.game_root}")
        print(f"Mods dir: {project.mods_dir}")
        print(f"Staging dir: {project.staging_dir}")
        print(f"Profile: {project.game_profile.display_name} ({project.game_profile.id})")
    return 0


def handle_project_set_paths(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    changed: list[str] = []
    if args.game_root is not None:
        project.game_root = normalize_path(args.game_root)
        changed.append("game_root")
    if args.mods_dir is not None:
        project.mods_dir = normalize_path(args.mods_dir)
        changed.append("mods_dir")
    if args.staging_dir is not None:
        project.staging_dir = normalize_path(args.staging_dir)
        changed.append("staging_dir")
    if not changed:
        print("No project paths were changed.")
        return 0
    project.save(args.project_file)
    print("Updated project paths: " + ", ".join(changed))
    return 0


def handle_project_export(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    payload = export_project(project, args.out, include_manifests=not args.no_manifests)
    print(f"Wrote project export: {args.out}")
    print("Includes manifests: yes" if payload["includes"]["manifests"] else "Includes manifests: no")
    print("Game files, mod archives, and backup binaries were not included.")
    return 0


def handle_project_import(args: argparse.Namespace) -> int:
    import_project(args.export_file, args.target, args.project_file_name)
    print(f"Imported project to {args.target / args.project_file_name}")
    return 0


def handle_project_audit(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    report = audit_project(project)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_project_audit(report.to_dict()))
    return 1 if report.has_errors else 0


def handle_profiles(args: argparse.Namespace) -> int:
    profiles = builtin_profiles()
    if args.json:
        print(json.dumps([profile.to_dict() for profile in profiles], indent=2))
    else:
        for profile in profiles:
            print(f"{profile.id:16} {profile.display_name}")
    return 0


def handle_profiles_validate(args: argparse.Namespace) -> int:
    profile = load_profile_file(args.profile_file)
    report = validate_profile(profile)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_profile_validation(report.to_dict()))
    return 1 if report.has_errors else 0


def handle_profiles_preview_map(args: argparse.Namespace) -> int:
    profile = load_profile_file(args.profile_file)
    report = validate_profile(profile)
    mappings = preview_profile_dir(profile, args.sample_mod_dir)
    payload = {
        "profile": profile.to_dict(),
        "validation": report.to_dict(),
        "mappings": [mapping.to_dict() for mapping in mappings],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_profile_validation(report.to_dict()))
        print(format_profile_preview(payload))
    return 1 if report.has_errors else 0


def handle_profiles_import(args: argparse.Namespace) -> int:
    try:
        destination = import_profile_file(args.profile_file, args.profile_dir, force=args.force)
    except ValueError as exc:
        print(str(exc))
        return 1
    profile = load_profile_file(destination)
    if args.json:
        print(json.dumps({"imported": str(destination), "profile": profile.to_dict()}, indent=2))
    else:
        print(f"Imported profile {profile.id}: {destination}")
        print(f"Profile dir: {Path(args.profile_dir) if args.profile_dir else custom_profile_dir()}")
    return 0


def handle_profiles_export(args: argparse.Namespace) -> int:
    profile = builtin_profile(args.profile_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps({"exported": str(args.out), "profile": profile.to_dict()}, indent=2))
    else:
        print(f"Exported profile {profile.id}: {args.out}")
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    report = run_doctor(args.project_file)
    formatted = format_doctor_report(report)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(formatted)
    if args.health_report:
        args.health_report.parent.mkdir(parents=True, exist_ok=True)
        args.health_report.write_text(formatted, encoding="utf-8")
    return report.exit_code(strict=args.strict)


def handle_scan_mods(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    packages = scan_project_mods(project)
    payload = [package.to_dict() for package in packages]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for package in packages:
            print(f"{package.priority:03d} {'on ' if package.enabled else 'off'} {package.name}")
    return 0


def handle_plan(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    plan = build_deployment_plan(project, scan_project_mods(project))
    if args.json:
        payload = summarize_deployment_plan(plan) if args.summary else plan.to_dict()
        print(json.dumps(payload, indent=2))
    elif args.summary:
        print(format_plan_summary(summarize_deployment_plan(plan)))
    else:
        print(f"Operations: {len(plan.operations)}")
        print(f"Conflicts: {len(plan.conflicts)}")
        for conflict in plan.conflicts:
            print(f"- {conflict.destination_path}: winner={conflict.winning_mod}")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    plan = build_deployment_plan(project, scan_project_mods(project))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_deployment_report(project, plan), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def handle_manifests_list(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    summaries = list_manifest_summaries(project)
    if args.json:
        print(json.dumps([summary.to_dict() for summary in summaries], indent=2))
    else:
        for summary in summaries:
            state = "restorable" if summary.can_restore else "blocked"
            print(f"{summary.manifest_id} {summary.target:7} {state:10} {summary.applied_at}")
    return 0


def handle_manifests_latest(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    summary = latest_manifest_summary(project)
    if summary is None:
        print("No manifests found.")
        return 1
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(format_manifest_summary(summary.to_dict()))
    return 0


def handle_manifests_show(args: argparse.Namespace) -> int:
    project = ModProject.load(args.project_file)
    summary = summarize_manifest(find_manifest(project, args.manifest))
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(format_manifest_summary(summary.to_dict()))
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
    packages = scan_project_mods(project)
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
    packages = scan_project_mods(project)
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
    manifest_path = _resolve_manifest_arg(args.project_file, args.manifest)
    if args.preview:
        preview = preview_restore_manifest(manifest_path, args.paths)
        if args.json:
            print(json.dumps(preview.to_dict(), indent=2))
        else:
            print(format_restore_preview(preview.to_dict()))
        return 0

    if not args.yes:
        print("Refusing to restore without --yes.")
        return 2

    manifest = restore_manifest(manifest_path, args.paths)
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2))
    else:
        print(f"Restored manifest: {manifest.manifest_id}")
        print(f"Target root: {manifest.target_root}")
        if args.paths:
            print(f"Selected paths: {len(args.paths)}")
    return 0


def handle_translation_extract(args: argparse.Namespace) -> int:
    entries = extract_strings(args.source)
    write_entries_csv(entries, args.output)
    if args.json:
        print(json.dumps({"entries": len(entries), "output": str(args.output)}, indent=2))
    else:
        print(f"Extracted {len(entries)} strings to {args.output}")
    return 0


def format_plan_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            f"Project: {summary['project_name']}",
            f"Risk: {summary['risk_level']}",
            f"Operations: {summary['operations']}",
            f"Winning operations: {summary['winning_operations']}",
            f"Skipped by conflict: {summary['skipped_by_conflict']}",
            f"Conflicts: {summary['conflicts']}",
            f"Warnings: {summary['warnings']}",
        ]
    )


def format_manifest_summary(summary: dict[str, object]) -> str:
    lines = [
        f"Manifest: {summary['manifest_id']}",
        f"Target: {summary['target']}",
        f"Target root: {summary['target_root']}",
        f"Applied: {summary['applied_at']}",
        f"Restored: {summary['restored_at'] or '-'}",
        f"Copied: {summary['copied']}",
        f"Overwritten: {summary['overwritten']}",
        f"Skipped: {summary['skipped']}",
        f"Backups: {summary['backups']}",
        f"Restorable records: {summary['restorable']}",
        f"Can restore: {'yes' if summary['can_restore'] else 'no'}",
        f"Path: {summary['path']}",
    ]
    for warning in summary.get("warnings", []):
        lines.append(f"WARNING: {warning}")
    return "\n".join(lines)


def format_project_audit(report: dict[str, object]) -> str:
    lines = [f"Project audit: {report['project_name']}"]
    for issue in report["issues"]:
        lines.append(f"{issue['status'].upper():7} {issue['name']}: {issue['message']}")
    return "\n".join(lines)


def format_profile_validation(report: dict[str, object]) -> str:
    lines = [f"Profile validation: {report['profile_id']}"]
    for issue in report["issues"]:
        lines.append(f"{issue['status'].upper():7} {issue['name']}: {issue['message']}")
    return "\n".join(lines)


def format_profile_preview(payload: dict[str, object]) -> str:
    lines = ["Preview mapping:"]
    for mapping in payload["mappings"]:  # type: ignore[index]
        destination = mapping["destination_path"] or "-"  # type: ignore[index]
        group = f" group={mapping['group_id']}" if mapping.get("group_id") else ""  # type: ignore[union-attr]
        lines.append(
            f"- {mapping['source_path']} -> {destination} "
            f"rule={mapping['rule_id'] or '-'} tier={mapping['safety_tier']}{group}"
        )
        for warning in mapping.get("warnings", []):  # type: ignore[union-attr]
            lines.append(f"  WARNING: {warning}")
    return "\n".join(lines)


def format_restore_preview(preview: dict[str, object]) -> str:
    records = preview.get("records", [])
    warnings = preview.get("warnings", [])
    lines = [
        f"Manifest: {preview.get('manifest_id')}",
        f"Target root: {preview.get('target_root')}",
        f"Selected paths: {len(preview.get('selected_paths', []))}",
        f"Can restore: {'yes' if preview.get('can_restore') else 'no'}",
        f"Will restore backups: {preview.get('restore_from_backup', 0)}",
        f"Will delete newly copied files: {preview.get('delete_copied_files', 0)}",
        f"Restore actions: {len(records)}",
    ]
    for warning in warnings:
        lines.append(f"WARNING: {warning}")
    for record in records:
        lines.append(
            f"- {record['destination_path']}: {record['action']} "
            f"({record['status']}, mod={record['source_mod']})"
        )
        if record.get("warning"):
            lines.append(f"  WARNING: {record['warning']}")
    return "\n".join(lines)


def _resolve_manifest_arg(project_file: Path, manifest_arg: Path) -> Path:
    if manifest_arg.exists():
        return manifest_arg
    project = ModProject.load(project_file)
    return find_manifest(project, str(manifest_arg))


if __name__ == "__main__":
    raise SystemExit(main())
