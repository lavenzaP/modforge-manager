"""Loose folder adapter."""

from __future__ import annotations

from pathlib import Path

from modforge.containers.base import ContainerInfo


def detect(path: Path) -> ContainerInfo | None:
    if path.is_dir():
        return ContainerInfo(container_type="loose_folder", supported=True)
    return None
