"""Backup policy helpers."""

from __future__ import annotations

from pathlib import Path


def backup_required(destination: Path) -> bool:
    """Return whether a destination should be backed up before destructive writes."""

    return destination.exists()
