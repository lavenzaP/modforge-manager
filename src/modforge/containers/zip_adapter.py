"""ZIP adapter."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from modforge.containers.base import ContainerInfo


def detect(path: Path) -> ContainerInfo | None:
    if path.is_file() and path.suffix.lower() == ".zip":
        if not _can_open(path):
            return ContainerInfo(
                container_type="zip",
                supported=False,
                warnings=[f"ZIP archive cannot be opened: {path.name}"],
            )
        return ContainerInfo(container_type="zip", supported=True)
    return None


def list_files(path: Path) -> tuple[list[tuple[str, int]], list[str]]:
    """Return safe ZIP member paths and sizes with warnings."""

    files: list[tuple[str, int]] = []
    warnings: list[str] = []
    try:
        with ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized = _safe_member_path(member.filename)
                if normalized is None:
                    warnings.append(f"Ignored unsafe ZIP member path: {member.filename}")
                    continue
                files.append((normalized, member.file_size))
    except BadZipFile:
        warnings.append(f"ZIP archive cannot be opened: {path.name}")
    return sorted(files), warnings


def read_file(path: Path, relative_path: str) -> bytes:
    with ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if _safe_member_path(member.filename) == relative_path:
                return archive.read(member)
    raise KeyError(relative_path)


def _can_open(path: Path) -> bool:
    try:
        with ZipFile(path) as archive:
            archive.testzip()
        return True
    except BadZipFile:
        return False


def _safe_member_path(value: str) -> str | None:
    normalized = value.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return None
    drive_like = len(parts[0]) >= 2 and parts[0][1] == ":"
    if drive_like:
        return None
    return "/".join(parts)
