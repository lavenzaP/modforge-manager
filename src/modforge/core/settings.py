"""Global settings models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass(slots=True)
class GlobalSettings:
    recent_projects: list[str] = field(default_factory=list)
    default_workspace_dir: str = ""
    external_tools: dict[str, str] = field(default_factory=dict)
    ui_preferences: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "GlobalSettings":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
