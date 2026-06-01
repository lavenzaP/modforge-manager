"""Base container detection result."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ContainerInfo:
    container_type: str
    supported: bool
    warnings: list[str] = field(default_factory=list)
