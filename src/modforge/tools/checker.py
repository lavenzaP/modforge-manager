"""External tool path checker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modforge.tools.registry import KNOWN_TOOLS


@dataclass(frozen=True, slots=True)
class ToolCheck:
    tool_id: str
    label: str
    path: str
    exists: bool
    warning: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "label": self.label,
            "path": self.path,
            "exists": self.exists,
            "warning": self.warning,
        }


def check_tools(configured_paths: dict[str, str]) -> list[ToolCheck]:
    checks: list[ToolCheck] = []
    for tool_id, label in KNOWN_TOOLS.items():
        raw_path = configured_paths.get(tool_id, "")
        exists = bool(raw_path) and Path(raw_path).expanduser().exists()
        warning = "" if exists else f"{label} is not configured or the path does not exist."
        checks.append(ToolCheck(tool_id, label, raw_path, exists, warning))
    return checks
