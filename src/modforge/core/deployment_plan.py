"""Dry-run deployment planning."""

from __future__ import annotations

from dataclasses import dataclass, field

from modforge.core.conflict_detector import Conflict, detect_conflicts
from modforge.core.mod_package import ModPackage
from modforge.core.mod_project import ModProject


@dataclass(frozen=True, slots=True)
class DeploymentOperation:
    source_mod: str
    source_path: str
    destination_path: str
    action: str = "copy"

    def to_dict(self) -> dict[str, object]:
        return {
            "source_mod": self.source_mod,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "action": self.action,
        }


@dataclass(slots=True)
class DeploymentPlan:
    project_name: str
    dry_run: bool = True
    operations: list[DeploymentOperation] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "dry_run": self.dry_run,
            "operations": [operation.to_dict() for operation in self.operations],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "warnings": self.warnings,
        }


def build_deployment_plan(project: ModProject, packages: list[ModPackage]) -> DeploymentPlan:
    operations: list[DeploymentOperation] = []
    conflict_entries: list[tuple[str, str, int]] = []
    warnings: list[str] = []
    rule = project.game_profile.deployment_rules[0]

    for package in packages:
        warnings.extend(f"{package.name}: {warning}" for warning in package.warnings)
        if not package.enabled:
            continue
        for mod_file in package.files:
            destination = rule.destination_for(package.path, package.path / mod_file.relative_path)
            operations.append(
                DeploymentOperation(
                    source_mod=package.name,
                    source_path=mod_file.relative_path,
                    destination_path=destination,
                )
            )
            conflict_entries.append((destination, package.name, package.priority))

    return DeploymentPlan(
        project_name=project.name,
        operations=operations,
        conflicts=detect_conflicts(conflict_entries),
        warnings=warnings,
    )
