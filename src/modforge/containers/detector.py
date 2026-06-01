"""Container detection facade."""

from __future__ import annotations

from pathlib import Path

from modforge.containers import godot_pck, loose_folder, unreal_pak, zip_adapter
from modforge.containers.base import ContainerInfo


ADAPTERS = [loose_folder.detect, zip_adapter.detect, godot_pck.detect, unreal_pak.detect]


def detect_container(path: Path) -> ContainerInfo:
    for adapter in ADAPTERS:
        result = adapter(path)
        if result is not None:
            return result
    return ContainerInfo(
        container_type="unknown",
        supported=False,
        warnings=[f"Unsupported package type: {path.name}"],
    )
