"""Godot PCK detector."""

from __future__ import annotations

from pathlib import Path

from modforge.containers.base import ContainerInfo


def detect(path: Path) -> ContainerInfo | None:
    if path.is_file() and path.suffix.lower() == ".pck":
        return ContainerInfo(container_type="godot_pck", supported=False)
    return None
