"""Project export/import/audit helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shlex

from modforge.core.manifest_browser import manifest_dir_for_project
from modforge.core.mod_project import ModProject
from modforge.core.user_profile import normalize_profile_id

EXPORT_FORMAT = "modforge-project-export-v1"


@dataclass(frozen=True, slots=True)
class ProjectAuditIssue:
    name: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectAuditReport:
    project_name: str
    issues: list[ProjectAuditIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.status == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.status == "warning" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def export_project(project: ModProject, output_path: Path, include_manifests: bool = True) -> dict[str, object]:
    payload = {
        "format": EXPORT_FORMAT,
        "project": project.to_dict(),
        "includes": {
            "manifests": include_manifests,
            "game_files": False,
            "mod_files": False,
            "backup_files": False,
        },
        "warnings": [
            "This export stores configuration and metadata only.",
            "Game files, mod archives, and backup binaries are not included.",
            "Absolute paths may need remapping after import.",
        ],
    }
    if include_manifests:
        manifest_dir = manifest_dir_for_project(project)
        payload["manifests"] = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(manifest_dir.glob("*.json"))
        ] if manifest_dir.exists() else []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def import_project(export_path: Path, target_dir: Path, project_file_name: str = "modforge.project.json") -> ModProject:
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    if payload.get("format") != EXPORT_FORMAT:
        raise ValueError(f"Unsupported ModForge export format: {payload.get('format')}")
    target_dir.mkdir(parents=True, exist_ok=True)
    project_payload = dict(payload["project"])  # type: ignore[arg-type]
    project_payload["staging_dir"] = str(target_dir / ".modforge" / "staging")
    project = ModProject.load_dict(project_payload)
    imported_project_path = target_dir / project_file_name
    project.save(imported_project_path)

    manifest_dir = manifest_dir_for_project(project)
    for manifest in payload.get("manifests", []):
        manifest_id = str(manifest.get("manifest_id", ""))
        if not manifest_id:
            continue
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / f"{manifest_id}.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
    return project


def audit_project(project: ModProject) -> ProjectAuditReport:
    issues: list[ProjectAuditIssue] = [
        _directory_issue("game-root", project.game_root, required=False),
        _directory_issue("mods-dir", project.mods_dir, required=True),
        _directory_issue("staging-dir", project.staging_dir, required=False),
    ]

    active = normalize_profile_id(project.active_user_profile)
    known_profiles = {normalize_profile_id(profile.id) for profile in project.user_profiles}
    if active in known_profiles:
        issues.append(ProjectAuditIssue("user-profile", "ok", f"Active user profile: {active}"))
    else:
        issues.append(ProjectAuditIssue("user-profile", "warning", f"Missing active user profile: {active}"))

    for tool_id, tool_path in sorted(project.external_tools.items()):
        if tool_path and not _tool_path_exists(tool_path):
            issues.append(ProjectAuditIssue(f"tool:{tool_id}", "warning", f"Tool path is unavailable: {tool_path}"))

    manifest_dir = manifest_dir_for_project(project)
    if not manifest_dir.exists():
        issues.append(ProjectAuditIssue("manifests", "warning", f"Manifest directory is missing: {manifest_dir}"))
    else:
        manifest_paths = sorted(manifest_dir.glob("*.json"))
        issues.append(ProjectAuditIssue("manifests", "ok", f"{len(manifest_paths)} manifests found."))
        issues.extend(_manifest_issues(manifest_paths))

    return ProjectAuditReport(project_name=project.name, issues=issues)


def _directory_issue(name: str, path: Path, required: bool) -> ProjectAuditIssue:
    if path.exists() and path.is_dir():
        return ProjectAuditIssue(name, "ok", str(path))
    status = "error" if required else "warning"
    return ProjectAuditIssue(name, status, f"Directory is unavailable: {path}")


def _tool_path_exists(raw_path: str) -> bool:
    try:
        parts = shlex.split(raw_path, posix=False)
    except ValueError:
        return False
    if not parts:
        return False
    executable = parts[0].strip("\"'")
    return Path(executable).expanduser().exists()


def _manifest_issues(manifest_paths: list[Path]) -> list[ProjectAuditIssue]:
    issues: list[ProjectAuditIssue] = []
    for path in manifest_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            issues.append(ProjectAuditIssue(f"manifest:{path.name}", "error", f"Could not read manifest: {error}"))
            continue
        target_root = Path(str(payload.get("target_root", "")))
        if str(payload.get("target", "")) == "game" and not target_root.exists():
            issues.append(
                ProjectAuditIssue(
                    f"manifest:{path.name}",
                    "warning",
                    f"Target root is unavailable: {target_root}",
                )
            )
        for record in payload.get("records", []):
            backup_path = str(record.get("backup_path", ""))
            if record.get("status") == "overwritten" and backup_path and not Path(backup_path).exists():
                issues.append(
                    ProjectAuditIssue(
                        f"manifest:{path.name}",
                        "warning",
                        f"Backup is missing: {backup_path}",
                    )
                )
    return issues
