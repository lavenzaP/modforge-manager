"""Runtime and project smoke checks."""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from modforge import __version__
from modforge.core.game_profile import builtin_profiles
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject
from modforge.core.user_profile import normalize_profile_id
from modforge.tools.checker import check_tools


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DoctorReport:
    version: str = __version__
    project_file: str = ""
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(check.status == "error" for check in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(check.status == "warning" for check in self.checks)

    def exit_code(self, strict: bool = False) -> int:
        if self.has_errors:
            return 1
        if strict and self.has_warnings:
            return 1
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "project_file": self.project_file,
            "checks": [check.to_dict() for check in self.checks],
        }


def run_doctor(project_file: Path | None = None) -> DoctorReport:
    checks = [
        _check_python_version(),
        _check_profiles(),
        _check_tkinter(),
    ]
    project_path = project_file.resolve(strict=False) if project_file else None
    if project_path is not None:
        checks.extend(_check_project(project_path))
    return DoctorReport(project_file=str(project_path or ""), checks=checks)


def format_doctor_report(report: DoctorReport) -> str:
    lines = [f"ModForge Manager {report.version} doctor", ""]
    if report.project_file:
        lines.append(f"Project file: {report.project_file}")
        lines.append("")
    for check in report.checks:
        lines.append(f"{check.status.upper():7} {check.name}: {check.message}")
    return "\n".join(lines)


def _check_python_version() -> DoctorCheck:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= (3, 12):
        return DoctorCheck("python", "ok", f"Python {version}")
    return DoctorCheck("python", "error", f"Python {version}; Python 3.12+ is required.")


def _check_profiles() -> DoctorCheck:
    profiles = builtin_profiles()
    if profiles:
        return DoctorCheck("profiles", "ok", f"{len(profiles)} built-in profiles available.")
    return DoctorCheck("profiles", "error", "No built-in game profiles are available.")


def _check_tkinter() -> DoctorCheck:
    try:
        import tkinter  # noqa: F401
    except Exception as error:  # pragma: no cover - platform dependent
        return DoctorCheck("tkinter", "warning", f"tkinter GUI is unavailable: {error}")
    return DoctorCheck("tkinter", "ok", "tkinter GUI runtime is available.")


def _check_project(project_path: Path) -> list[DoctorCheck]:
    if not project_path.exists():
        return [
            DoctorCheck("project-file", "warning", f"Project file does not exist: {project_path}")
        ]
    try:
        project = ModProject.load(project_path)
    except (AttributeError, OSError, KeyError, TypeError, ValueError) as error:
        return [DoctorCheck("project-file", "error", f"Could not load project: {error}")]

    mods_dir_check = _check_directory("mods-dir", project.mods_dir, required=True)
    checks: list[DoctorCheck] = [
        DoctorCheck("project-file", "ok", f"Loaded project {project.name}."),
        _check_directory("game-root", project.game_root, required=False),
        mods_dir_check,
        _check_active_user_profile(project),
    ]
    checks.extend(_check_tool_paths(project))
    if mods_dir_check.status == "ok":
        checks.append(_check_scan(project))
    else:
        checks.append(
            DoctorCheck(
                "scan",
                "error",
                f"Skipped because mods directory is unavailable: {project.mods_dir}",
            )
        )
    return checks


def _check_directory(name: str, path: Path, required: bool) -> DoctorCheck:
    if path.exists() and path.is_dir():
        return DoctorCheck(name, "ok", str(path))
    status = "error" if required else "warning"
    return DoctorCheck(name, status, f"Directory is unavailable: {path}")


def _check_active_user_profile(project: ModProject) -> DoctorCheck:
    active = normalize_profile_id(project.active_user_profile)
    known = {normalize_profile_id(profile.id) for profile in project.user_profiles}
    if active in known:
        return DoctorCheck("user-profile", "ok", f"Active user profile: {active}")
    return DoctorCheck(
        "user-profile",
        "warning",
        f"Active profile is missing and will be recreated: {active}",
    )


def _check_tool_paths(project: ModProject) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    for check in check_tools(project.external_tools):
        status = "ok" if check.exists else "warning"
        message = check.path if check.exists else check.warning
        checks.append(DoctorCheck(f"tool:{check.tool_id}", status, message))
    return checks


def _check_scan(project: ModProject) -> DoctorCheck:
    try:
        packages = scan_mods(project.mods_dir, project.active_profile())
    except OSError as error:
        return DoctorCheck("scan", "error", f"Could not scan mods directory: {error}")
    warnings = sum(len(package.warnings) for package in packages)
    message = f"{len(packages)} packages scanned"
    if warnings:
        message += f"; {warnings} package warnings"
    return DoctorCheck("scan", "ok", message)
