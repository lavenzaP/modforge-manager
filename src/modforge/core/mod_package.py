"""Mod package scanning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from modforge.containers import external_archive, zip_adapter
from modforge.containers.detector import detect_container
from modforge.core.paths import as_posix_relative, iter_files, normalize_path
from modforge.core.user_profile import UserProfile

if TYPE_CHECKING:
    from modforge.core.mod_project import ModProject


@dataclass(frozen=True, slots=True)
class ModFile:
    relative_path: str
    size: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ModPackage:
    id: str
    name: str
    path: Path
    enabled: bool
    priority: int
    detected_type: str
    files: list[ModFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extracted_path: Path | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "enabled": self.enabled,
            "priority": self.priority,
            "detected_type": self.detected_type,
            "files": [file.to_dict() for file in self.files],
            "warnings": self.warnings,
            "extracted_path": str(self.extracted_path) if self.extracted_path else "",
        }


def scan_project_mods(project: "ModProject") -> list[ModPackage]:
    return scan_mods(
        project.mods_dir,
        project.active_profile(),
        external_tools=project.external_tools,
        extraction_dir=project.staging_dir.parent / "extracted",
    )


def scan_mods(
    mods_dir: str | Path,
    user_profile: UserProfile | None = None,
    external_tools: dict[str, str] | None = None,
    extraction_dir: Path | None = None,
) -> list[ModPackage]:
    root = normalize_path(mods_dir)
    if not root.exists():
        return []

    packages: list[ModPackage] = []
    for index, item in enumerate(sorted(root.iterdir(), key=lambda path: path.name.lower())):
        if item.name.startswith("."):
            continue
        detected = detect_container(item)
        warnings = list(detected.warnings)
        extracted_path: Path | None = None
        if detected.container_type == "loose_folder":
            files = _scan_loose_files(item)
            warnings.extend(_loose_unreal_sidecar_warnings(files))
        elif detected.container_type == "zip" and detected.supported:
            file_entries, zip_warnings = zip_adapter.list_files(item)
            files = [
                ModFile(relative_path=relative_path, size=size)
                for relative_path, size in file_entries
            ]
            warnings.extend(zip_warnings)
        elif detected.container_type in external_archive.TOOL_IDS:
            if _has_external_tool(detected.container_type, external_tools or {}):
                result = external_archive.extract_archive(
                    item,
                    detected.container_type,
                    external_tools or {},
                    extraction_dir,
                )
                files = [
                    ModFile(relative_path=relative_path, size=size)
                    for relative_path, size in result.files
                ]
                extracted_path = result.extracted_path
                warnings.extend(result.warnings)
            else:
                files = [ModFile(relative_path=item.name, size=item.stat().st_size)]
                warnings.append(
                    f"No external tool configured for {detected.container_type}: "
                    f"{external_archive.TOOL_IDS[detected.container_type]}; deploying archive as-is."
                )
        else:
            files = []
        if detected.supported is False and not files:
            warnings.append(f"{detected.container_type} detection is present, extraction is deferred.")
        warnings.extend(_family_warnings(item, detected.container_type))
        packages.append(
            ModPackage(
                id=item.stem.lower().replace(" ", "-"),
                name=item.stem if item.is_file() else item.name,
                path=item,
                enabled=user_profile.is_enabled(item.stem.lower().replace(" ", "-"))
                if user_profile
                else True,
                priority=user_profile.priority_for(item.stem.lower().replace(" ", "-"), index)
                if user_profile
                else index,
                detected_type=detected.container_type,
                files=files,
                warnings=warnings,
                extracted_path=extracted_path,
            )
        )
    return packages


def _family_warnings(path: Path, container_type: str) -> list[str]:
    if container_type == "unreal_pak":
        return _unreal_sidecar_warnings(path)
    return []


def _unreal_sidecar_warnings(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix not in {".pak", ".ucas", ".utoc"}:
        return []
    if suffix == ".pak" and not path.with_suffix(".ucas").exists() and not path.with_suffix(".utoc").exists():
        return []
    base = path.with_suffix("")
    siblings = {suffix: base.with_suffix(suffix).exists() for suffix in [".pak", ".ucas", ".utoc"]}
    present = [suffix for suffix, exists in siblings.items() if exists]
    if len(present) == 1 and path.suffix.lower() == ".pak":
        return []
    missing = [suffix for suffix, exists in siblings.items() if not exists]
    if missing:
        return [
            f"Unreal sidecar set is incomplete for {base.name}: missing {', '.join(missing)}"
        ]
    return []


def _loose_unreal_sidecar_warnings(files: list[ModFile]) -> list[str]:
    groups: dict[str, set[str]] = {}
    for mod_file in files:
        path = Path(mod_file.relative_path)
        suffix = path.suffix.lower()
        if suffix not in {".pak", ".ucas", ".utoc"}:
            continue
        groups.setdefault(str(path.with_suffix("")).replace("\\", "/"), set()).add(suffix)

    warnings: list[str] = []
    for base, suffixes in sorted(groups.items()):
        if suffixes == {".pak"}:
            continue
        missing = [suffix for suffix in [".pak", ".ucas", ".utoc"] if suffix not in suffixes]
        if missing:
            warnings.append(
                f"Unreal sidecar set is incomplete for {Path(base).name}: missing {', '.join(missing)}"
            )
    return warnings


def _has_external_tool(container_type: str, external_tools: dict[str, str]) -> bool:
    tool_id = external_archive.TOOL_IDS.get(container_type)
    return bool(tool_id and external_tools.get(tool_id, "").strip())


def _scan_loose_files(mod_root: Path) -> list[ModFile]:
    return [
        ModFile(relative_path=as_posix_relative(path, mod_root), size=path.stat().st_size)
        for path in iter_files(mod_root)
    ]
