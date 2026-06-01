"""Mod package scanning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from modforge.containers import zip_adapter
from modforge.containers.detector import detect_container
from modforge.core.paths import as_posix_relative, iter_files, normalize_path
from modforge.core.user_profile import UserProfile


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
        }


def scan_mods(mods_dir: str | Path, user_profile: UserProfile | None = None) -> list[ModPackage]:
    root = normalize_path(mods_dir)
    if not root.exists():
        return []

    packages: list[ModPackage] = []
    for index, item in enumerate(sorted(root.iterdir(), key=lambda path: path.name.lower())):
        if item.name.startswith("."):
            continue
        detected = detect_container(item)
        warnings = list(detected.warnings)
        if detected.container_type == "loose_folder":
            files = _scan_loose_files(item)
        elif detected.container_type == "zip" and detected.supported:
            file_entries, zip_warnings = zip_adapter.list_files(item)
            files = [
                ModFile(relative_path=relative_path, size=size)
                for relative_path, size in file_entries
            ]
            warnings.extend(zip_warnings)
        else:
            files = []
        if detected.supported is False:
            warnings.append(f"{detected.container_type} detection is present, extraction is deferred.")
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
            )
        )
    return packages


def _scan_loose_files(mod_root: Path) -> list[ModFile]:
    return [
        ModFile(relative_path=as_posix_relative(path, mod_root), size=path.stat().st_size)
        for path in iter_files(mod_root)
    ]
