"""Safe staging deployment executor."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from modforge.core.deployment_plan import DeploymentPlan
from modforge.core.manifest import InstallManifest
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
    manifest = InstallManifest(manifest_id=str(uuid4()))

    for operation in plan.operations:
        if winners.get(operation.destination_path, operation.source_mod) != operation.source_mod:
            manifest.skipped_files.append(operation.destination_path)
            continue

        package = package_by_name[operation.source_mod]
        source = package.path / operation.source_path
        destination = _safe_destination(staging_dir, operation.destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            manifest.overwritten_files.append(operation.destination_path)
        else:
            manifest.copied_files.append(operation.destination_path)
        shutil.copy2(source, destination)

    manifest_path = staging_dir / ".modforge-install-manifest.json"
    manifest.save(manifest_path)
    return manifest


def _safe_destination(staging_dir: Path, destination_path: str) -> Path:
    destination = (staging_dir / destination_path).resolve(strict=False)
    try:
        destination.relative_to(staging_dir)
    except ValueError as exc:
        raise ValueError(f"Refusing to write outside staging directory: {destination_path}") from exc
    return destination
