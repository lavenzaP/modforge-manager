"""Path helpers."""

from __future__ import annotations

from pathlib import Path


def normalize_path(path: str | Path) -> Path:
    """Return an expanded, non-strict absolute path."""

    return Path(path).expanduser().resolve(strict=False)


def iter_files(root: Path) -> list[Path]:
    """Return all files below root in stable relative order."""

    if not root.exists() or not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def as_posix_relative(path: Path, root: Path) -> str:
    """Return a stable slash-separated path relative to root."""

    return path.relative_to(root).as_posix()
