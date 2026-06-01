"""Unreal PAK detector."""

from __future__ import annotations

from pathlib import Path

from modforge.containers.base import ContainerInfo


def detect(path: Path) -> ContainerInfo | None:
    if path.is_file() and path.suffix.lower() in {".pak", ".ucas", ".utoc"}:
        return ContainerInfo(container_type="unreal_pak", supported=False)
    return None
