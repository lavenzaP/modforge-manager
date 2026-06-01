"""Safe staging deployment executor."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from modforge.containers import zip_adapter
from modforge.core.conflict_detector import conflict_path_key
from modforge.core.deployment_plan import DeploymentOperation, DeploymentPlan
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.mod_package import ModPackage
from modforge.core.mod_project import ModProject
from modforge.core.paths import has_link_component, is_link_or_junction


@dataclass(frozen=True, slots=True)
class RestorePreviewRecord:
    destination_path: str
    status: str
    source_mod: str
    action: str
    backup_path: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RestorePreview:
    manifest_id: str
    target_root: str
    selected_paths: list[str] = field(default_factory=list)
    records: list[RestorePreviewRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        missing_backups = [
            record.backup_path
            for record in self.records
            if record.warning.startswith("Backup is missing")
            and record.backup_path
        ]
        return {
            "manifest_id": self.manifest_id,
            "target_root": self.target_root,
            "selected_paths": self.selected_paths,
            "can_restore": not self.warnings,
            "restore_from_backup": sum(1 for record in self.records if record.action == "restore-backup"),
            "delete_copied_files": sum(1 for record in self.records if record.action == "remove-created-file"),
            "missing_backups": missing_backups,
            "records": [record.to_dict() for record in self.records],
            "warnings": self.warnings,
        }


@dataclass(frozen=True, slots=True)
class _RestoreAction:
    record: InstallRecord
    destination: Path
    action: str
    backup: Path | None = None
    warning: str = ""


@dataclass(frozen=True, slots=True)
class _PreparedOperation:
    operation: DeploymentOperation
    package: ModPackage
    destination: Path
    backup: Path | None = None
    backup_path: str = ""


def apply_to_staging(project: ModProject, plan: DeploymentPlan, packages: list[ModPackage]) -> InstallManifest:
    """Apply the winning dry-run operations to the project's staging directory.

    This function intentionally writes only to `project.staging_dir`. It does not
    mutate the configured game root.
    """

    staging_dir = project.staging_dir.resolve(strict=False)
    staging_dir.mkdir(parents=True, exist_ok=True)
    winners = _conflict_winners(plan)
    prepared = _prepare_operations(plan, packages, staging_dir, winners)
    manifest = InstallManifest(
        manifest_id=str(uuid4()),
        target="staging",
        target_root=str(staging_dir),
    )

    for operation in plan.operations:
        if _is_skipped_by_conflict(operation, winners):
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

        prepared_operation = prepared[id(operation)]
        package = prepared_operation.package
        destination = prepared_operation.destination
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
    winners = _conflict_winners(plan)
    prepared = _prepare_operations(plan, packages, game_root, winners, backup_dir)
    manifest = InstallManifest(
        manifest_id=manifest_id,
        target="game",
        target_root=str(game_root),
        backup_dir=str(backup_dir),
    )

    for operation in plan.operations:
        if _is_skipped_by_conflict(operation, winners):
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

        prepared_operation = prepared[id(operation)]
        package = prepared_operation.package
        destination = prepared_operation.destination
        backup_path = prepared_operation.backup_path
        if destination.exists():
            backup = prepared_operation.backup
            if backup is None:
                raise FileNotFoundError(f"Backup path was not prepared: {operation.destination_path}")
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
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


def preview_restore_manifest(manifest_path: Path, selected_paths: Iterable[str] | None = None) -> RestorePreview:
    """Return the game files a restore would touch without writing anything."""

    manifest = InstallManifest.load(manifest_path)
    if manifest.target != "game":
        raise ValueError(f"Only game manifests can be restored, got: {manifest.target}")
    target_root = Path(manifest.target_root).resolve(strict=False)
    selected = _expand_atomic_sidecar_selection(manifest, _normalize_selected_paths(selected_paths))
    restorable_records, unmatched = _matching_restore_records(manifest, selected)

    warnings: list[str] = []
    if not target_root.exists() or not target_root.is_dir():
        warnings.append(f"Manifest target root is unavailable: {target_root}")
    if selected == set():
        warnings.append("No restore paths were selected.")
    warnings.extend(f"No restorable record matched selected path: {path}" for path in unmatched)

    records: list[RestorePreviewRecord] = []
    for record in restorable_records:
        restore_action = _validate_restore_record(manifest, target_root, record, strict=False)
        if restore_action.warning:
            warning = restore_action.warning
            warnings.append(warning)
        else:
            warning = ""
        records.append(
            RestorePreviewRecord(
                destination_path=record.destination_path,
                status=record.status,
                source_mod=record.source_mod,
                action=restore_action.action,
                backup_path=record.backup_path,
                warning=warning,
            )
        )

    return RestorePreview(
        manifest_id=manifest.manifest_id,
        target_root=manifest.target_root,
        selected_paths=sorted(selected or []),
        records=records,
        warnings=warnings,
    )


def restore_manifest(manifest_path: Path, selected_paths: Iterable[str] | None = None) -> InstallManifest:
    """Restore a previously applied game manifest."""

    manifest = InstallManifest.load(manifest_path)
    if manifest.target != "game":
        raise ValueError(f"Only game manifests can be restored, got: {manifest.target}")
    target_root = Path(manifest.target_root).resolve(strict=False)
    if not target_root.exists() or not target_root.is_dir():
        raise FileNotFoundError(f"Manifest target root is unavailable: {target_root}")

    selected = _expand_atomic_sidecar_selection(manifest, _normalize_selected_paths(selected_paths))
    restorable_records, unmatched = _matching_restore_records(manifest, selected)
    if selected == set():
        raise ValueError("No restore paths were selected.")
    if unmatched:
        raise ValueError(f"No restorable records matched selected paths: {', '.join(unmatched)}")

    restore_actions = [
        _validate_restore_record(manifest, target_root, record, strict=True)
        for record in restorable_records
    ]

    for restore_action in reversed(restore_actions):
        destination = restore_action.destination
        if restore_action.action == "restore-backup":
            if restore_action.backup is None:
                raise FileNotFoundError(
                    f"Backup is missing for overwritten record: {restore_action.record.destination_path}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(restore_action.backup, destination)
        elif restore_action.action == "remove-created-file" and destination.exists():
            destination.unlink()

    manifest.restored_at = datetime.now(UTC).isoformat()
    manifest.save(manifest_path)
    return manifest


def _safe_destination(target_root: Path, destination_path: str) -> Path:
    root = target_root.resolve(strict=False)
    parts = _safe_relative_parts(destination_path)
    destination = root.joinpath(*parts)
    if has_link_component(destination, root):
        raise ValueError(f"Refusing to write through linked path component: {destination_path}")
    resolved = destination.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Refusing to write outside target root: {destination_path}") from exc
    return destination


def _write_operation_source(package: ModPackage, relative_path: str, destination: Path) -> None:
    if package.detected_type == "loose_folder":
        shutil.copy2(_safe_source(package.path, relative_path), destination)
        return
    if package.detected_type in {"godot_pck", "unreal_pak"} and package.extracted_path is None:
        shutil.copy2(package.path, destination)
        return
    if package.detected_type == "zip":
        destination.write_bytes(zip_adapter.read_file(package.path, relative_path))
        return
    if package.detected_type in {"godot_pck", "unreal_pak"}:
        if package.extracted_path is None:
            raise ValueError(f"Package was not extracted before deployment: {package.name}")
        source = _safe_source(package.extracted_path, relative_path)
        shutil.copy2(source, destination)
        return
    raise ValueError(f"Package type cannot be staged yet: {package.detected_type}")


def _conflict_winners(plan: DeploymentPlan) -> dict[str, str]:
    return {conflict_path_key(conflict.destination_path): conflict.winning_mod for conflict in plan.conflicts}


def _is_skipped_by_conflict(operation: DeploymentOperation, winners: dict[str, str]) -> bool:
    return winners.get(conflict_path_key(operation.destination_path), operation.source_mod) != operation.source_mod


def _prepare_operations(
    plan: DeploymentPlan,
    packages: list[ModPackage],
    target_root: Path,
    winners: dict[str, str],
    backup_root: Path | None = None,
) -> dict[int, _PreparedOperation]:
    prepared: dict[int, _PreparedOperation] = {}
    for operation in plan.operations:
        if _is_skipped_by_conflict(operation, winners):
            continue
        package = _package_for_operation(packages, operation)
        _validate_operation_source(package, operation.source_path)
        destination = _safe_destination(target_root, operation.destination_path)
        backup: Path | None = None
        backup_path = ""
        if backup_root is not None and destination.exists():
            backup = _safe_destination(backup_root, operation.destination_path)
            backup_path = str(backup)
        prepared[id(operation)] = _PreparedOperation(
            operation=operation,
            package=package,
            destination=destination,
            backup=backup,
            backup_path=backup_path,
        )
    return prepared


def _package_for_operation(packages: list[ModPackage], operation: DeploymentOperation) -> ModPackage:
    if operation.source_package_path:
        for package in packages:
            if str(package.path) == operation.source_package_path:
                return package
        raise KeyError(f"Missing source package path: {operation.source_package_path}")

    matches = [package for package in packages if package.name == operation.source_mod]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Cannot uniquely resolve source package: {operation.source_mod}")


def _validate_operation_source(package: ModPackage, relative_path: str) -> None:
    if package.detected_type == "loose_folder":
        _safe_source(package.path, relative_path)
        return
    if package.detected_type in {"godot_pck", "unreal_pak"} and package.extracted_path is None:
        if is_link_or_junction(package.path) or not package.path.exists():
            raise ValueError(f"Refusing to deploy linked or missing archive package: {package.path}")
        return
    if package.detected_type == "zip":
        return
    if package.detected_type in {"godot_pck", "unreal_pak"}:
        if package.extracted_path is None:
            raise ValueError(f"Package was not extracted before deployment: {package.name}")
        _safe_source(package.extracted_path, relative_path)
        return
    raise ValueError(f"Package type cannot be staged yet: {package.detected_type}")


def _normalize_manifest_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _normalize_selected_paths(selected_paths: Iterable[str] | None) -> set[str] | None:
    if selected_paths is None:
        return None
    return {_normalize_manifest_path(path) for path in selected_paths}


_UNREAL_SIDECAR_SUFFIXES = {".pak", ".ucas", ".utoc"}


def _expand_atomic_sidecar_selection(
    manifest: InstallManifest,
    selected: set[str] | None,
) -> set[str] | None:
    if selected is None or not selected:
        return selected

    groups: dict[str, set[str]] = {}
    for record in manifest.records:
        if record.status == "skipped":
            continue
        key = _unreal_sidecar_key(record.destination_path)
        if key is None:
            continue
        groups.setdefault(key, set()).add(_normalize_manifest_path(record.destination_path))

    expanded = set(selected)
    selected_keys = {_unreal_sidecar_key(path) for path in selected}
    selected_keys.discard(None)
    for key in selected_keys:
        expanded.update(groups.get(key, set()))
    return expanded


def _unreal_sidecar_key(destination_path: str) -> str | None:
    normalized = _normalize_manifest_path(destination_path)
    path = PurePosixPath(normalized)
    if path.suffix.lower() not in _UNREAL_SIDECAR_SUFFIXES:
        return None
    return str(path.with_suffix("")).casefold()


def _matching_restore_records(
    manifest: InstallManifest,
    selected: set[str] | None,
) -> tuple[list[InstallRecord], list[str]]:
    restorable_records = [record for record in manifest.records if record.status != "skipped"]
    if selected is None:
        return restorable_records, []

    matched_records: list[InstallRecord] = []
    matched_paths: set[str] = set()
    for record in restorable_records:
        destination_path = _normalize_manifest_path(record.destination_path)
        if destination_path in selected:
            matched_records.append(record)
            matched_paths.add(destination_path)
    return matched_records, sorted(selected - matched_paths)


def _validate_restore_record(
    manifest: InstallManifest,
    target_root: Path,
    record: InstallRecord,
    strict: bool,
) -> _RestoreAction:
    try:
        destination = _safe_destination(target_root, record.destination_path)
    except ValueError as error:
        if strict:
            raise
        return _RestoreAction(
            record=record,
            destination=target_root,
            action="blocked",
            warning=str(error),
        )
    if record.status == "copied":
        return _RestoreAction(record=record, destination=destination, action="remove-created-file")

    if record.status != "overwritten":
        return _blocked_or_raise(
            record,
            destination,
            f"Cannot restore manifest record with status {record.status!r}: {record.destination_path}",
            strict,
        )

    if not record.backup_path:
        return _blocked_or_raise(
            record,
            destination,
            f"Backup is missing for overwritten record: {record.destination_path}",
            strict,
        )
    if not manifest.backup_dir:
        return _blocked_or_raise(
            record,
            destination,
            f"Backup directory is missing for overwritten record: {record.destination_path}",
            strict,
        )

    backup = Path(record.backup_path).resolve(strict=False)
    backup_root = Path(manifest.backup_dir).resolve(strict=False)
    try:
        backup.relative_to(backup_root)
    except ValueError:
        return _blocked_or_raise(
            record,
            destination,
            f"Backup is outside manifest backup directory: {record.backup_path}",
            strict,
        )
    if not backup.exists():
        return _blocked_or_raise(
            record,
            destination,
            f"Backup is missing: {backup}",
            strict,
        )
    return _RestoreAction(
        record=record,
        destination=destination,
        action="restore-backup",
        backup=backup,
    )


def _blocked_or_raise(
    record: InstallRecord,
    destination: Path,
    warning: str,
    strict: bool,
) -> _RestoreAction:
    if strict:
        if warning.startswith("Backup is missing"):
            raise FileNotFoundError(warning)
        raise ValueError(warning)
    return _RestoreAction(
        record=record,
        destination=destination,
        action="blocked",
        warning=warning,
    )


def _safe_source(root: Path, relative_path: str) -> Path:
    if is_link_or_junction(root):
        raise ValueError(f"Refusing to read through linked package root: {root}")
    source_root = root.resolve(strict=False)
    source = source_root.joinpath(*_safe_relative_parts(relative_path))
    if has_link_component(source, source_root):
        raise ValueError(f"Refusing to read through linked package path: {relative_path}")
    resolved = source.resolve(strict=False)
    try:
        resolved.relative_to(source_root)
    except ValueError as exc:
        raise ValueError(f"Refusing to read outside extracted package: {relative_path}") from exc
    return source


def _safe_relative_parts(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError(f"Refusing absolute path: {path}")
    parts = tuple(part for part in normalized.split("/") if part not in {"", "."})
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Refusing unsafe relative path: {path}")
    if len(parts[0]) >= 2 and parts[0][1] == ":":
        raise ValueError(f"Refusing drive-prefixed path: {path}")
    return parts
