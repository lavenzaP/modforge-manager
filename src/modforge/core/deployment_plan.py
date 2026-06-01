"""Dry-run deployment planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from modforge.core.conflict_detector import Conflict, conflict_path_key, detect_conflicts
from modforge.core.game_profile import DeploymentRule
from modforge.core.mod_package import ModPackage
from modforge.core.mod_project import ModProject


@dataclass(frozen=True, slots=True)
class DeploymentOperation:
    source_mod: str
    source_path: str
    destination_path: str
    action: str = "copy"
    source_package_path: str = ""
    source_priority: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "source_mod": self.source_mod,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "action": self.action,
            "source_package_path": self.source_package_path,
            "source_priority": self.source_priority,
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


def summarize_deployment_plan(plan: DeploymentPlan) -> dict[str, object]:
    winners = {conflict_path_key(conflict.destination_path): conflict.winning_mod for conflict in plan.conflicts}
    skipped_by_conflict = [
        operation
        for operation in plan.operations
        if winners.get(conflict_path_key(operation.destination_path), operation.source_mod) != operation.source_mod
    ]
    if plan.conflicts:
        risk_level = "high"
    elif plan.warnings:
        risk_level = "medium"
    else:
        risk_level = "low"
    return {
        "project_name": plan.project_name,
        "dry_run": plan.dry_run,
        "operations": len(plan.operations),
        "winning_operations": len(plan.operations) - len(skipped_by_conflict),
        "skipped_by_conflict": len(skipped_by_conflict),
        "conflicts": len(plan.conflicts),
        "warnings": len(plan.warnings),
        "risk_level": risk_level,
    }


def build_deployment_plan(project: ModProject, packages: list[ModPackage]) -> DeploymentPlan:
    operations: list[DeploymentOperation] = []
    warnings: list[str] = []

    for package in packages:
        warnings.extend(f"{package.name}: {warning}" for warning in package.warnings)
        if package.detected_type not in project.game_profile.supported_containers:
            warnings.append(
                f"{package.name}: {package.detected_type} is not supported by "
                f"{project.game_profile.display_name}."
            )
            continue
        if not package.enabled:
            continue
        for mod_file in package.files:
            if _ignored(mod_file.relative_path, project.game_profile.ignored_patterns):
                continue
            rule = _rule_for(mod_file.relative_path, project.game_profile.deployment_rules)
            if rule is None:
                warnings.append(f"{package.name}: no deployment rule for {mod_file.relative_path}")
                continue
            destination = rule.destination_for_relative(mod_file.relative_path)
            operations.append(
                DeploymentOperation(
                    source_mod=package.name,
                    source_path=mod_file.relative_path,
                    destination_path=destination,
                    source_package_path=str(package.path),
                    source_priority=package.priority,
                )
            )

    operations = _drop_same_mod_destination_duplicates(operations, warnings)
    conflict_entries = [
        (operation.destination_path, operation.source_mod, operation.source_priority)
        for operation in operations
    ]

    return DeploymentPlan(
        project_name=project.name,
        operations=operations,
        conflicts=detect_conflicts(conflict_entries),
        warnings=warnings,
    )


def _ignored(relative_path: str, patterns: list[str]) -> bool:
    return any(fnmatchcase(relative_path, pattern) for pattern in patterns)


def _rule_for(relative_path: str, rules: list[DeploymentRule]) -> DeploymentRule | None:
    for rule in sorted(rules, key=lambda item: item.priority):
        if rule.matches(relative_path):
            return rule
    return None


def _drop_same_mod_destination_duplicates(
    operations: list[DeploymentOperation],
    warnings: list[str],
) -> list[DeploymentOperation]:
    grouped: dict[tuple[str, str], list[DeploymentOperation]] = {}
    for operation in operations:
        source_key = operation.source_package_path or operation.source_mod
        grouped.setdefault((source_key, conflict_path_key(operation.destination_path)), []).append(operation)

    kept: list[DeploymentOperation] = []
    skipped: set[int] = set()
    for group in grouped.values():
        if len(group) <= 1:
            continue
        ordered = sorted(
            group,
            key=lambda item: (
                item.destination_path.casefold(),
                item.destination_path,
                item.source_path.casefold(),
                item.source_path,
            ),
        )
        winner = ordered[0]
        skipped.update(id(item) for item in ordered[1:])
        skipped_sources = ", ".join(item.source_path for item in ordered[1:])
        warnings.append(
            f"{winner.source_mod}: duplicate destination variants resolve to the same Windows path; "
            f"keeping {winner.source_path}, skipping {skipped_sources}"
        )

    for operation in operations:
        if id(operation) not in skipped:
            kept.append(operation)
    return kept
