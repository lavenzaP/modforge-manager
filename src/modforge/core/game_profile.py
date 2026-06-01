"""Game profile and deployment rule models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeploymentRule:
    source_pattern: str = "**/*"
    destination_root: str = ""
    destination_pattern: str = "{relative_path}"
    priority: int = 0
    enabled: bool = True

    def destination_for(self, mod_root: Path, file_path: Path) -> str:
        relative_path = file_path.relative_to(mod_root).as_posix()
        destination = self.destination_pattern.format(relative_path=relative_path)
        if self.destination_root:
            return f"{self.destination_root.strip('/')}/{destination}".strip("/")
        return destination

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GameProfile:
    id: str
    display_name: str
    deployment_rules: list[DeploymentRule] = field(default_factory=lambda: [DeploymentRule()])
    ignored_patterns: list[str] = field(default_factory=list)
    supported_containers: list[str] = field(
        default_factory=lambda: ["loose_folder", "zip", "godot_pck", "unreal_pak"]
    )

    @classmethod
    def generic(cls) -> "GameProfile":
        return cls(id="generic-folder", display_name="Generic Folder Game")

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "GameProfile":
        rules = [
            DeploymentRule(**item)
            for item in value.get("deployment_rules", [])  # type: ignore[arg-type]
        ] or [DeploymentRule()]
        return cls(
            id=str(value.get("id", "generic-folder")),
            display_name=str(value.get("display_name", "Generic Folder Game")),
            deployment_rules=rules,
            ignored_patterns=list(value.get("ignored_patterns", [])),  # type: ignore[arg-type]
            supported_containers=list(value.get("supported_containers", [])),  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "deployment_rules": [rule.to_dict() for rule in self.deployment_rules],
            "ignored_patterns": self.ignored_patterns,
            "supported_containers": self.supported_containers,
        }
