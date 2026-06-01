"""Translation workspace model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TranslationWorkspace:
    root: Path

    @property
    def source_dir(self) -> Path:
        return self.root / "source"

    @property
    def target_dir(self) -> Path:
        return self.root / "target"
