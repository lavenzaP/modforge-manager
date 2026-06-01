"""Install manifest placeholder models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path


@dataclass(slots=True)
class InstallManifest:
    manifest_id: str
    applied_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    copied_files: list[str] = field(default_factory=list)
    overwritten_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "applied_at": self.applied_at,
            "copied_files": self.copied_files,
            "overwritten_files": self.overwritten_files,
            "skipped_files": self.skipped_files,
            "backups": self.backups,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
