"""Path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def normalize_path(path: str | Path) -> Path:
    """Return an expanded, non-strict absolute path."""

    return Path(path).expanduser().resolve(strict=False)


def iter_files(root: Path) -> list[Path]:
    """Return all files below root in stable relative order."""

    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = [
            name
            for name in dirnames
            if not is_link_or_junction(current_path / name)
        ]
        for filename in filenames:
            path = current_path / filename
            if path.is_file() and not has_link_component(path, root):
                files.append(path)
    return sorted(files)


def as_posix_relative(path: Path, root: Path) -> str:
    """Return a stable slash-separated path relative to root."""

    return path.relative_to(root).as_posix()


def has_link_component(path: Path, root: Path) -> bool:
    """Return true when a path or parent below root is a symlink/junction."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    current = root
    for part in relative.parts:
        current = current / part
        if is_link_or_junction(current):
            return True
    return False


def is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or _is_junction(path)


def _is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())
