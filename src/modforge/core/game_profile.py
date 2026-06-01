"""Game profile and deployment rule models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeploymentRule:
    source_pattern: str = "**/*"
    destination_root: str = ""
    destination_pattern: str = "{relative_path}"
    priority: int = 0
    enabled: bool = True

    def matches(self, relative_path: str) -> bool:
        if not self.enabled:
            return False
        if fnmatchcase(relative_path, self.source_pattern):
            return True
        if self.source_pattern.startswith("**/"):
            return fnmatchcase(relative_path, self.source_pattern[3:])
        return False

    def destination_for(self, mod_root: Path, file_path: Path) -> str:
        relative_path = file_path.relative_to(mod_root).as_posix()
        return self.destination_for_relative(relative_path)

    def destination_for_relative(self, relative_path: str) -> str:
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
        return builtin_profile("generic-folder")

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "GameProfile":
        rules = [
            DeploymentRule(**item)
            for item in value.get("deployment_rules", [])  # type: ignore[arg-type]
        ] or [DeploymentRule()]
        supported = value.get("supported_containers")
        return cls(
            id=str(value.get("id", "generic-folder")),
            display_name=str(value.get("display_name", "Generic Folder Game")),
            deployment_rules=rules,
            ignored_patterns=list(value.get("ignored_patterns", [])),  # type: ignore[arg-type]
            supported_containers=list(supported)  # type: ignore[arg-type]
            if supported is not None
            else ["loose_folder", "zip", "godot_pck", "unreal_pak"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "deployment_rules": [rule.to_dict() for rule in self.deployment_rules],
            "ignored_patterns": self.ignored_patterns,
            "supported_containers": self.supported_containers,
        }


def builtin_profiles() -> list[GameProfile]:
    return [
        GameProfile(
            id="generic-folder",
            display_name="Generic Folder Game",
            deployment_rules=[DeploymentRule()],
            ignored_patterns=[".modforge/**", "**/.DS_Store", "**/Thumbs.db"],
        ),
        GameProfile(
            id="mo2-mod",
            display_name="Mod Organizer 2 Mod Folder",
            deployment_rules=[DeploymentRule()],
            ignored_patterns=["meta.ini", "INI Tweaks/**", ".mohidden/**", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="godot-pck",
            display_name="Godot PCK Mod Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="*.pck", destination_root="mods"),
                DeploymentRule(source_pattern="**/*.pck", destination_root="mods"),
                DeploymentRule(source_pattern="**/*"),
            ],
            ignored_patterns=[".import/**", "*.import", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip", "godot_pck"],
        ),
        GameProfile(
            id="unreal-pak",
            display_name="Unreal PAK ~mods Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="*.pak", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="*.ucas", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="*.utoc", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="**/*.pak", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="**/*.ucas", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="**/*.utoc", destination_root="Content/Paks/~mods"),
                DeploymentRule(source_pattern="**/*"),
            ],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip", "unreal_pak"],
        ),
        GameProfile(
            id="sts2-mods",
            display_name="Slay the Spire 2 Mods Folder",
            deployment_rules=[DeploymentRule(destination_root="mods")],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="reframework",
            display_name="REFramework / NativePC Game Folder",
            deployment_rules=[DeploymentRule()],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
    ]


def builtin_profile(profile_id: str) -> GameProfile:
    for profile in builtin_profiles():
        if profile.id == profile_id:
            return profile
    raise KeyError(f"Unknown game profile: {profile_id}")
