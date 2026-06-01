"""Install manifest models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path


@dataclass(slots=True)
class InstallRecord:
    destination_path: str
    source_mod: str = ""
    source_path: str = ""
    status: str = ""
    backup_path: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "InstallRecord":
        return cls(
            destination_path=str(value.get("destination_path", "")),
            source_mod=str(value.get("source_mod", "")),
            source_path=str(value.get("source_path", "")),
            status=str(value.get("status", "")),
            backup_path=str(value.get("backup_path", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class InstallManifest:
    manifest_id: str
    target: str = "staging"
    target_root: str = ""
    backup_dir: str = ""
    applied_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    restored_at: str = ""
    copied_files: list[str] = field(default_factory=list)
    overwritten_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    records: list[InstallRecord] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "InstallManifest":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "InstallManifest":
        return cls(
            manifest_id=str(value["manifest_id"]),
            target=str(value.get("target", "staging")),
            target_root=str(value.get("target_root", "")),
            backup_dir=str(value.get("backup_dir", "")),
            applied_at=str(value.get("applied_at", "")),
            restored_at=str(value.get("restored_at", "")),
            copied_files=list(value.get("copied_files", [])),  # type: ignore[arg-type]
            overwritten_files=list(value.get("overwritten_files", [])),  # type: ignore[arg-type]
            skipped_files=list(value.get("skipped_files", [])),  # type: ignore[arg-type]
            backups=list(value.get("backups", [])),  # type: ignore[arg-type]
            records=[
                InstallRecord.from_dict(item)
                for item in value.get("records", [])  # type: ignore[union-attr]
            ],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "target": self.target,
            "target_root": self.target_root,
            "backup_dir": self.backup_dir,
            "applied_at": self.applied_at,
            "restored_at": self.restored_at,
            "copied_files": self.copied_files,
            "overwritten_files": self.overwritten_files,
            "skipped_files": self.skipped_files,
            "backups": self.backups,
            "records": [record.to_dict() for record in self.records],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
