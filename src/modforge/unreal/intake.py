"""Read-only Unreal mod package intake reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from modforge.core.game_profile import GameProfile, ProfileMapping, preview_profile_paths, validate_profile


ARCHIVE_EXTENSIONS = {".pak", ".ucas", ".utoc"}
HIGH_RISK_TIERS = {"runtime-file", "dll-high-risk", "high-risk"}
RUNTIME_DLL_NAMES = {"dwmapi.dll", "ue4ss.dll", "version.dll"}


@dataclass(slots=True)
class UnrealIntakeOperation:
    source_path: str
    destination_path: str
    rule_id: str
    action: str
    safety_tier: str
    category: str
    group_id: str = ""
    high_risk: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class UnrealSidecarGroup:
    group_id: str
    files: list[str]
    present_extensions: list[str]
    missing_extensions: list[str]
    complete: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class UnrealIntakeReport:
    profile_id: str
    source: str
    source_kind: str
    package_shape: str
    operations_preview: list[UnrealIntakeOperation]
    sidecar_groups: list[UnrealSidecarGroup]
    high_risk_files: list[UnrealIntakeOperation]
    unmanaged_files: list[UnrealIntakeOperation]
    warnings: list[str]
    blocked: list[str]
    validation: dict[str, object]

    @property
    def ok(self) -> bool:
        return not self.blocked and not bool(self.validation.get("has_errors"))

    def summary(self) -> dict[str, int]:
        categories = {}
        for operation in self.operations_preview:
            categories[operation.category] = categories.get(operation.category, 0) + 1
        return {
            "files": len(self.operations_preview),
            "sidecar_groups": len(self.sidecar_groups),
            "high_risk_files": len(self.high_risk_files),
            "unmanaged_files": len(self.unmanaged_files),
            "warnings": len(self.warnings),
            "blocked": len(self.blocked),
            **{f"category_{key}": value for key, value in sorted(categories.items())},
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "profile_id": self.profile_id,
            "source": self.source,
            "source_kind": self.source_kind,
            "package_shape": self.package_shape,
            "summary": self.summary(),
            "operations_preview": [operation.to_dict() for operation in self.operations_preview],
            "sidecar_groups": [group.to_dict() for group in self.sidecar_groups],
            "high_risk_files": [operation.to_dict() for operation in self.high_risk_files],
            "unmanaged_files": [operation.to_dict() for operation in self.unmanaged_files],
            "warnings": self.warnings,
            "blocked": self.blocked,
            "validation": self.validation,
        }


def build_unreal_intake_report(profile: GameProfile, source: str | Path) -> UnrealIntakeReport:
    source_path = Path(source)
    source_kind, relative_paths, blocked = _list_source_paths(source_path)
    validation = validate_profile(profile).to_dict()
    mappings = preview_profile_paths(profile, relative_paths, package_name=_package_name(source_path))
    operations = [_operation_from_mapping(mapping) for mapping in mappings]
    sidecar_groups = _build_sidecar_groups(profile, mappings)
    warnings = _collect_warnings(operations, sidecar_groups)
    if not relative_paths and not blocked:
        warnings.append("No files were found in the source package.")
    return UnrealIntakeReport(
        profile_id=profile.id,
        source=str(source_path),
        source_kind=source_kind,
        package_shape=_package_shape_from_operations(operations),
        operations_preview=operations,
        sidecar_groups=sidecar_groups,
        high_risk_files=[operation for operation in operations if operation.high_risk],
        unmanaged_files=[operation for operation in operations if operation.action == "unmanaged"],
        warnings=warnings,
        blocked=blocked,
        validation=validation,
    )


def format_unreal_intake_report(report: UnrealIntakeReport) -> str:
    lines = [
        f"Unreal intake: {report.profile_id}",
        f"Source: {report.source}",
        f"Source kind: {report.source_kind}",
        f"Package shape: {report.package_shape}",
        f"Files: {len(report.operations_preview)}",
        f"Sidecar groups: {len(report.sidecar_groups)}",
        f"High-risk files: {len(report.high_risk_files)}",
        f"Unmanaged files: {len(report.unmanaged_files)}",
    ]
    for warning in report.warnings:
        lines.append(f"WARNING: {warning}")
    for blocked in report.blocked:
        lines.append(f"BLOCKED: {blocked}")
    for operation in report.operations_preview:
        destination = operation.destination_path or "-"
        group = f" group={operation.group_id}" if operation.group_id else ""
        risk = " high-risk" if operation.high_risk else ""
        lines.append(
            f"- {operation.source_path} -> {destination} "
            f"{operation.category} rule={operation.rule_id or '-'} tier={operation.safety_tier}{group}{risk}"
        )
        for warning in operation.warnings:
            lines.append(f"  WARNING: {warning}")
    return "\n".join(lines)


def _list_source_paths(source: Path) -> tuple[str, list[str], list[str]]:
    if not source.exists():
        return "missing", [], [f"Source does not exist: {source}"]
    if source.is_file() and source.suffix.casefold() == ".zip":
        try:
            with ZipFile(source) as archive:
                paths = []
                blocked: list[str] = []
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    member = item.filename.replace("\\", "/")
                    if not _safe_source_member(member):
                        blocked.append(f"Unsafe zip member path was skipped: {item.filename}")
                        continue
                    paths.append(member.lstrip("/"))
        except BadZipFile:
            return "zip", [], [f"Source is not a readable zip archive: {source}"]
        return "zip", sorted(paths, key=str.casefold), blocked
    if source.is_file():
        return "file", [source.name], []
    paths = [
        path.relative_to(source).as_posix()
        for path in sorted(source.rglob("*"), key=lambda item: item.as_posix().casefold())
        if path.is_file()
    ]
    return "folder", paths, []


def _package_name(source: Path) -> str:
    if source.is_file():
        return source.stem
    return source.name


def _safe_source_member(member: str) -> bool:
    normalized = member.replace("\\", "/")
    if not normalized or normalized.startswith("/") or normalized.startswith("//"):
        return False
    if re.match(r"^[A-Za-z]:", normalized):
        return False
    parts = [part for part in normalized.split("/") if part]
    return ".." not in parts


def _operation_from_mapping(mapping: ProfileMapping) -> UnrealIntakeOperation:
    category = _classify_mapping(mapping)
    warnings = list(mapping.warnings)
    if category == "logicmods_experimental":
        warnings.append("LogicMods layout is experimental; verify the game-specific loader before applying.")
    if mapping.action == "unmanaged" and not warnings:
        warnings.append("No deployment rule matched this file.")
    high_risk = mapping.safety_tier in HIGH_RISK_TIERS or any(
        "high-risk" in warning.casefold() or "protected path" in warning.casefold()
        for warning in warnings
    )
    return UnrealIntakeOperation(
        source_path=mapping.source_path,
        destination_path=mapping.destination_path,
        rule_id=mapping.rule_id,
        action=mapping.action,
        safety_tier=mapping.safety_tier,
        category=category,
        group_id=mapping.group_id,
        high_risk=high_risk,
        warnings=warnings,
    )


def _classify_mapping(mapping: ProfileMapping) -> str:
    source = mapping.source_path.replace("\\", "/")
    lower = source.casefold()
    name = Path(source).name.casefold()
    suffix = Path(source).suffix.casefold()
    if mapping.action == "ignored":
        return "ignored"
    if _is_runtime_dll(name):
        return "runtime_dll"
    if lower.startswith("ue4ss/") or lower.startswith("sb/binaries/win64/ue4ss/"):
        return "ue4ss_runtime"
    if lower.startswith("logicmods/") or lower.startswith("sb/content/paks/logicmods/"):
        return "logicmods_experimental"
    if lower.startswith("sb/"):
        return "already_rooted_sb_package"
    if suffix in ARCHIVE_EXTENSIONS:
        return "flat_unreal_archive"
    if suffix == ".json" and mapping.rule_id == "cns-json-sidecar":
        return "cns_json_sidecar"
    if mapping.action == "unmanaged":
        return "unmanaged"
    return "mapped"


def _is_runtime_dll(name: str) -> bool:
    return name in RUNTIME_DLL_NAMES or fnmatchcase(name, "xinput*.dll")


def _build_sidecar_groups(profile: GameProfile, mappings: list[ProfileMapping]) -> list[UnrealSidecarGroup]:
    by_group: dict[str, list[ProfileMapping]] = {}
    for mapping in mappings:
        if mapping.group_id:
            by_group.setdefault(mapping.group_id, []).append(mapping)

    expected_by_group_id = {group.id: sorted(group.extensions) for group in profile.sidecar_groups}
    groups: list[UnrealSidecarGroup] = []
    for group_id, members in sorted(by_group.items()):
        prefix = group_id.split(":", 1)[0]
        expected = expected_by_group_id.get(prefix, [])
        present = sorted({Path(member.source_path).suffix.casefold() for member in members})
        missing = [extension for extension in expected if extension not in present]
        warnings = sorted({warning for member in members for warning in member.warnings})
        groups.append(
            UnrealSidecarGroup(
                group_id=group_id,
                files=[member.source_path for member in members],
                present_extensions=present,
                missing_extensions=missing,
                complete=not missing,
                warnings=warnings,
            )
        )
    return groups


def _collect_warnings(operations: list[UnrealIntakeOperation], groups: list[UnrealSidecarGroup]) -> list[str]:
    warnings = sorted({warning for operation in operations for warning in operation.warnings})
    for group in groups:
        if not group.complete:
            warnings.append(f"{group.group_id} is incomplete: missing {', '.join(group.missing_extensions)}")
    return warnings


def _package_shape_from_operations(operations: list[UnrealIntakeOperation]) -> str:
    categories = {operation.category for operation in operations if operation.category != "ignored"}
    if not categories:
        return "empty"
    has_archive = "flat_unreal_archive" in categories or any(
        operation.group_id for operation in operations
    )
    has_runtime = bool(categories & {"ue4ss_runtime", "runtime_dll"})
    has_rooted = "already_rooted_sb_package" in categories
    has_logicmods = "logicmods_experimental" in categories
    if sum([has_archive, has_runtime, has_rooted, has_logicmods]) >= 2:
        return "mixed_unreal_package"
    if categories <= {"flat_unreal_archive", "cns_json_sidecar"}:
        return "flat_unreal_archive"
    if categories == {"already_rooted_sb_package"}:
        return "already_rooted_sb_package"
    if categories == {"ue4ss_runtime"}:
        return "ue4ss_runtime_package"
    if categories == {"runtime_dll"}:
        return "runtime_dll_package"
    if categories == {"logicmods_experimental"}:
        return "logicmods_package"
    if categories == {"unmanaged"}:
        return "unknown"
    return "mixed_unreal_package"
