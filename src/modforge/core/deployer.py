"""Safe staging deployment executor."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4
from datetime import UTC, datetime

from modforge.containers import zip_adapter
from modforge.core.deployment_plan import DeploymentPlan
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.mod_package import ModPackage
from modforge.core.mod_project import ModProject


def apply_to_staging(project: ModProject, plan: DeploymentPlan, packages: list[ModPackage]) -> InstallManifest:
    """Apply the winning dry-run operations to the project's staging directory.

    This function intentionally writes only to `project.staging_dir`. It does not
    mutate the configured game root.
    """

    staging_dir = project.staging_dir.resolve(strict=False)
    staging_dir.mkdir(parents=True, exist_ok=True)
    package_by_name = {package.name: package for package in packages}
    winners = {conflict.destination_path: conflict.winning_mod for conflict in plan.conflicts}
    manifest = InstallManifest(
        manifest_id=str(uuid4()),
        target="staging",
        target_root=str(staging_dir),
    )

    for operation in plan.operations:
        if winners.get(operation.destination_path, operation.source_mod) != operation.source_mod:
            manifest.skipped_files.append(operation.destination_path)
            manifest.records.append(
                InstallRecord(
                    destination_path=operation.destination_path,
                    source_mod=operation.source_mod,
                    source_path=operation.source_path,
                    status="skipped",
                )
            )
            continue

        package = package_by_name[operation.source_mod]
        destination = _safe_destination(staging_dir, operation.destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            manifest.overwritten_files.append(operation.destination_path)
            status = "overwritten"
        else:
            manifest.copied_files.append(operation.destination_path)
            status = "copied"
        _write_operation_source(package, operation.source_path, destination)
        manifest.records.append(
            InstallRecord(
                destination_path=operation.destination_path,
                source_mod=operation.source_mod,
                source_path=operation.source_path,
                status=status,
            )
        )

    manifest_path = staging_dir / ".modforge-install-manifest.json"
    manifest.save(manifest_path)
    return manifest


def apply_to_game(project: ModProject, plan: DeploymentPlan, packages: list[ModPackage]) -> InstallManifest:
    """Apply winning operations to the game root with backups and a manifest."""

    game_root = project.game_root.resolve(strict=False)
    if not game_root.exists() or not game_root.is_dir():
        raise FileNotFoundError(f"Game root does not exist or is not a directory: {game_root}")

    manifest_id = str(uuid4())
    workspace_dir = project.staging_dir.parent.resolve(strict=False)
    backup_dir = workspace_dir / "backups" / manifest_id
    manifest_path = workspace_dir / "manifests" / f"{manifest_id}.json"
    package_by_name = {package.name: package for package in packages}
    winners = {conflict.destination_path: conflict.winning_mod for conflict in plan.conflicts}
    manifest = InstallManifest(
        manifest_id=manifest_id,
        target="game",
        target_root=str(game_root),
        backup_dir=str(backup_dir),
    )

    for operation in plan.operations:
        if winners.get(operation.destination_path, operation.source_mod) != operation.source_mod:
            manifest.skipped_files.append(operation.destination_path)
            manifest.records.append(
                InstallRecord(
                    destination_path=operation.destination_path,
                    source_mod=operation.source_mod,
                    source_path=operation.source_path,
                    status="skipped",
                )
            )
            continue

        package = package_by_name[operation.source_mod]
        destination = _safe_destination(game_root, operation.destination_path)
        backup_path = ""
        if destination.exists():
            backup = _safe_destination(backup_dir, operation.destination_path)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
            backup_path = str(backup)
            manifest.backups.append(operation.destination_path)
            manifest.overwritten_files.append(operation.destination_path)
            status = "overwritten"
        else:
            manifest.copied_files.append(operation.destination_path)
            status = "copied"

        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_operation_source(package, operation.source_path, destination)
        manifest.records.append(
            InstallRecord(
                destination_path=operation.destination_path,
                source_mod=operation.source_mod,
                source_path=operation.source_path,
                status=status,
                backup_path=backup_path,
            )
        )

    manifest.save(manifest_path)
    return manifest


def restore_manifest(manifest_path: Path, selected_paths: Iterable[str] | None = None) -> InstallManifest:
    """Restore a previously applied game manifest."""

    manifest = InstallManifest.load(manifest_path)
    if manifest.target != "game":
        raise ValueError(f"Only game manifests can be restored, got: {manifest.target}")
    target_root = Path(manifest.target_root).resolve(strict=False)
    if not target_root.exists() or not target_root.is_dir():
        raise FileNotFoundError(f"Manifest target root is unavailable: {target_root}")

    selected = {_normalize_manifest_path(path) for path in selected_paths} if selected_paths is not None else None
    restorable_records = [
        record
        for record in manifest.records
        if record.status != "skipped" and (selected is None or _normalize_manifest_path(record.destination_path) in selected)
    ]
    if selected is not None and not restorable_records:
        raise ValueError("No restorable records matched the selected paths.")

    for record in reversed(restorable_records):
        if record.status == "skipped":
            continue
        destination = _safe_destination(target_root, record.destination_path)
        if record.backup_path:
            backup = Path(record.backup_path)
            if not backup.exists():
                raise FileNotFoundError(f"Backup is missing: {backup}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, destination)
        elif record.status == "copied" and destination.exists():
            destination.unlink()

    manifest.restored_at = datetime.now(UTC).isoformat()
    manifest.save(manifest_path)
    return manifest


def _safe_destination(staging_dir: Path, destination_path: str) -> Path:
    destination = (staging_dir / destination_path).resolve(strict=False)
    try:
        destination.relative_to(staging_dir)
    except ValueError as exc:
        raise ValueError(f"Refusing to write outside staging directory: {destination_path}") from exc
    return destination


def _write_operation_source(package: ModPackage, relative_path: str, destination: Path) -> None:
    if package.detected_type == "loose_folder":
        shutil.copy2(package.path / relative_path, destination)
        return
    if package.detected_type == "zip":
        destination.write_bytes(zip_adapter.read_file(package.path, relative_path))
        return
    raise ValueError(f"Package type cannot be staged yet: {package.detected_type}")


def _normalize_manifest_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")
