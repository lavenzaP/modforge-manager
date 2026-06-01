"""Unreal PAK adapter stub."""

from __future__ import annotations

from pathlib import Path

from modforge.containers.base import ContainerInfo


def detect(path: Path) -> ContainerInfo | None:
    if path.is_file() and path.suffix.lower() == ".pak":
        return ContainerInfo(container_type="unreal_pak", supported=False)
    return None
