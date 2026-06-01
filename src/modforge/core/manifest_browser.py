"""Manifest discovery and restore availability helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from modforge.core.deployer import preview_restore_manifest
from modforge.core.manifest import InstallManifest
from modforge.core.mod_project import ModProject


@dataclass(frozen=True, slots=True)
class ManifestSummary:
    manifest_id: str
    path: str
    target: str
    target_root: str
    applied_at: str
    restored_at: str
    copied: int
    overwritten: int
    skipped: int
    backups: int
    restorable: int
    can_restore: bool
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def manifest_dir_for_project(project: ModProject) -> Path:
    return project.staging_dir.parent / "manifests"


def list_manifest_summaries(project: ModProject) -> list[ManifestSummary]:
    manifest_dir = manifest_dir_for_project(project)
    if not manifest_dir.exists():
        return []
    paths = sorted(manifest_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [_safe_summarize_manifest(path) for path in paths]


def latest_manifest_summary(project: ModProject) -> ManifestSummary | None:
    summaries = list_manifest_summaries(project)
    return summaries[0] if summaries else None


def summarize_manifest(manifest_path: Path) -> ManifestSummary:
    manifest = InstallManifest.load(manifest_path)
    warnings: list[str] = []
    can_restore = False
    restorable = sum(1 for record in manifest.records if record.status != "skipped")
    if manifest.target == "game":
        preview = preview_restore_manifest(manifest_path)
        warnings = list(preview.warnings)
        can_restore = bool(preview.to_dict()["can_restore"])
        restorable = len(preview.records)
    else:
        warnings.append("Only game manifests can be restored.")
    return ManifestSummary(
        manifest_id=manifest.manifest_id,
        path=str(manifest_path),
        target=manifest.target,
        target_root=manifest.target_root,
        applied_at=manifest.applied_at,
        restored_at=manifest.restored_at,
        copied=len(manifest.copied_files),
        overwritten=len(manifest.overwritten_files),
        skipped=len(manifest.skipped_files),
        backups=len(manifest.backups),
        restorable=restorable,
        can_restore=can_restore,
        warnings=warnings,
    )


def _safe_summarize_manifest(manifest_path: Path) -> ManifestSummary:
    try:
        return summarize_manifest(manifest_path)
    except (OSError, ValueError, KeyError) as error:
        return ManifestSummary(
            manifest_id=manifest_path.stem,
            path=str(manifest_path),
            target="invalid",
            target_root="",
            applied_at="",
            restored_at="",
            copied=0,
            overwritten=0,
            skipped=0,
            backups=0,
            restorable=0,
            can_restore=False,
            warnings=[f"Could not read manifest: {error}"],
        )


def find_manifest(project: ModProject, manifest_id_or_path: str) -> Path:
    candidate = Path(manifest_id_or_path)
    if candidate.exists():
        return candidate
    manifest_dir = manifest_dir_for_project(project)
    matches = sorted(manifest_dir.glob(f"{manifest_id_or_path}*.json"))
    if not matches:
        raise FileNotFoundError(f"Manifest was not found: {manifest_id_or_path}")
    if len(matches) > 1:
        raise ValueError(f"Manifest id is ambiguous: {manifest_id_or_path}")
    return matches[0]
