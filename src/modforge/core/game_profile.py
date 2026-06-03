"""Game profile and deployment rule models."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from string import Formatter


PROFILE_SCHEMA_VERSION = 1
CUSTOM_PROFILE_ENV = "MODFORGE_PROFILE_DIR"
_SAFE_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ALLOWED_FORMAT_FIELDS = {"relative_path", "filename", "stem", "package_id", "package_name"}


@dataclass(frozen=True, slots=True)
class DeploymentRule:
    id: str = ""
    source_pattern: str = "**/*"
    source_patterns: list[str] = field(default_factory=list)
    destination_root: str = ""
    destination_pattern: str = "{relative_path}"
    priority: int = 0
    enabled: bool = True
    mode: str = "copy"
    safety_tier: str = "normal"
    requires_extra_confirmation: bool = False
    container_types: list[str] = field(default_factory=list)
    exclude_container_types: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "DeploymentRule":
        patterns = value.get("source_patterns", [])
        return cls(
            id=str(value.get("id", "")),
            source_pattern=str(value.get("source_pattern", "**/*")),
            source_patterns=[str(item) for item in patterns],  # type: ignore[arg-type]
            destination_root=str(value.get("destination_root", "")),
            destination_pattern=str(value.get("destination_pattern", "{relative_path}")),
            priority=int(value.get("priority", 0)),
            enabled=bool(value.get("enabled", True)),
            mode=str(value.get("mode", "copy")),
            safety_tier=str(value.get("safety_tier", "normal")),
            requires_extra_confirmation=bool(value.get("requires_extra_confirmation", False)),
            container_types=[str(item) for item in value.get("container_types", [])],  # type: ignore[arg-type]
            exclude_container_types=[str(item) for item in value.get("exclude_container_types", [])],  # type: ignore[arg-type]
            notes=str(value.get("notes", "")),
        )

    @property
    def patterns(self) -> list[str]:
        return self.source_patterns or [self.source_pattern]

    @property
    def specificity(self) -> int:
        return max((len(pattern.replace("*", "")) for pattern in self.patterns), default=0)

    def matches(self, relative_path: str) -> bool:
        if not self.enabled:
            return False
        return any(_matches_pattern(relative_path, pattern) for pattern in self.patterns)

    def accepts_container(self, container_type: str) -> bool:
        if self.container_types and container_type not in self.container_types:
            return False
        return container_type not in self.exclude_container_types

    def destination_for(self, mod_root: Path, file_path: Path, root_aliases: dict[str, str] | None = None) -> str:
        relative_path = file_path.relative_to(mod_root).as_posix()
        return self.destination_for_relative(relative_path, root_aliases=root_aliases)

    def destination_for_relative(
        self,
        relative_path: str,
        *,
        package_id: str = "",
        package_name: str = "",
        root_aliases: dict[str, str] | None = None,
    ) -> str:
        filename = Path(relative_path).name
        stem = Path(filename).stem
        destination = self.destination_pattern.format(
            relative_path=relative_path,
            filename=filename,
            stem=stem,
            package_id=package_id,
            package_name=package_name,
        )
        root = self.destination_root
        if root_aliases and root in root_aliases:
            root = root_aliases[root]
        if root in {"", "."}:
            return destination.strip("/")
        return f"{root.strip('/')}/{destination}".strip("/")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if not self.id:
            payload.pop("id")
        if not self.source_patterns:
            payload.pop("source_patterns")
        if self.source_pattern == "**/*" and self.source_patterns:
            payload.pop("source_pattern")
        if self.mode == "copy":
            payload.pop("mode")
        if self.safety_tier == "normal":
            payload.pop("safety_tier")
        if not self.requires_extra_confirmation:
            payload.pop("requires_extra_confirmation")
        if not self.container_types:
            payload.pop("container_types")
        if not self.exclude_container_types:
            payload.pop("exclude_container_types")
        if not self.notes:
            payload.pop("notes")
        return payload


@dataclass(frozen=True, slots=True)
class SidecarGroupRule:
    id: str
    extensions: list[str]
    atomic: bool = True
    missing_behavior: str = "warning"
    stem_regex: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "SidecarGroupRule":
        return cls(
            id=str(value.get("id", "")),
            extensions=[str(item).lower() for item in value.get("extensions", [])],  # type: ignore[arg-type]
            atomic=bool(value.get("atomic", True)),
            missing_behavior=str(value.get("missing_behavior", "warning")),
            stem_regex=str(value.get("stem_regex", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationSample:
    source: str
    expected_destination: str

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "ValidationSample":
        return cls(
            source=str(value.get("source", "")),
            expected_destination=str(value.get("expected_destination", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ProfileMapping:
    source_path: str
    destination_path: str
    rule_id: str
    safety_tier: str
    action: str = "copy"
    group_id: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileValidationIssue:
    status: str
    name: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileValidationReport:
    profile_id: str
    issues: list[ProfileValidationIssue]

    @property
    def has_errors(self) -> bool:
        return any(issue.status == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "has_errors": self.has_errors,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class GameProfile:
    id: str
    display_name: str
    deployment_rules: list[DeploymentRule] = field(default_factory=lambda: [DeploymentRule()])
    ignored_patterns: list[str] = field(default_factory=list)
    supported_containers: list[str] = field(
        default_factory=lambda: ["loose_folder", "zip", "godot_pck", "unreal_pak"]
    )
    schema_version: int = PROFILE_SCHEMA_VERSION
    family: str = ""
    description: str = ""
    root_aliases: dict[str, str] = field(default_factory=dict)
    sidecar_groups: list[SidecarGroupRule] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=list)
    validation_samples: list[ValidationSample] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    trust_level: str = "builtin"

    @classmethod
    def generic(cls) -> "GameProfile":
        return builtin_profile("generic-folder")

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "GameProfile":
        rules = [
            DeploymentRule.from_dict(item)
            for item in value.get("deployment_rules", [])  # type: ignore[arg-type]
        ] or [DeploymentRule()]
        supported = value.get("supported_containers")
        sidecar_groups = [
            SidecarGroupRule.from_dict(item)
            for item in value.get("sidecar_groups", [])  # type: ignore[arg-type]
        ]
        validation_samples = [
            ValidationSample.from_dict(item)
            for item in value.get("validation_samples", [])  # type: ignore[arg-type]
        ]
        return cls(
            id=str(value.get("id", "generic-folder")),
            display_name=str(value.get("display_name", "Generic Folder Game")),
            deployment_rules=rules,
            ignored_patterns=list(value.get("ignored_patterns", [])),  # type: ignore[arg-type]
            supported_containers=list(supported)  # type: ignore[arg-type]
            if supported is not None
            else ["loose_folder", "zip", "godot_pck", "unreal_pak"],
            schema_version=int(value.get("schema_version", PROFILE_SCHEMA_VERSION)),
            family=str(value.get("family", "")),
            description=str(value.get("description", "")),
            root_aliases={str(key): str(item) for key, item in dict(value.get("root_aliases", {})).items()},
            sidecar_groups=sidecar_groups,
            protected_paths=list(value.get("protected_paths", [])),  # type: ignore[arg-type]
            validation_samples=validation_samples,
            required_tools=list(value.get("required_tools", [])),  # type: ignore[arg-type]
            trust_level=str(value.get("trust_level", "custom")),
        )

    def matching_rule(self, relative_path: str, rules: list[DeploymentRule] | None = None) -> DeploymentRule | None:
        candidates = [
            rule
            for rule in (rules if rules is not None else self.deployment_rules)
            if rule.matches(relative_path)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda rule: (rule.priority, -rule.specificity, rule.id))[0]

    def destination_for_rule(
        self,
        rule: DeploymentRule,
        relative_path: str,
        *,
        package_id: str = "",
        package_name: str = "",
    ) -> str:
        return rule.destination_for_relative(
            relative_path,
            package_id=package_id,
            package_name=package_name,
            root_aliases=self.root_aliases,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "display_name": self.display_name,
            "deployment_rules": [rule.to_dict() for rule in self.deployment_rules],
            "ignored_patterns": self.ignored_patterns,
            "supported_containers": self.supported_containers,
        }
        if self.family:
            payload["family"] = self.family
        if self.description:
            payload["description"] = self.description
        if self.root_aliases:
            payload["root_aliases"] = self.root_aliases
        if self.sidecar_groups:
            payload["sidecar_groups"] = [group.to_dict() for group in self.sidecar_groups]
        if self.protected_paths:
            payload["protected_paths"] = self.protected_paths
        if self.validation_samples:
            payload["validation_samples"] = [sample.to_dict() for sample in self.validation_samples]
        if self.required_tools:
            payload["required_tools"] = self.required_tools
        if self.trust_level != "builtin":
            payload["trust_level"] = self.trust_level
        return payload


def load_profile_file(path: str | Path, *, trust_level: str = "custom") -> GameProfile:
    profile_path = Path(path)
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Profile JSON root must be an object: {profile_path}")
    payload.setdefault("trust_level", trust_level)
    return GameProfile.from_dict(payload)


def builtin_profiles() -> list[GameProfile]:
    return _code_builtin_profiles() + _json_builtin_profiles()


def all_profiles() -> list[GameProfile]:
    return builtin_profiles() + custom_profiles()


def custom_profile_dir() -> Path:
    configured = os.environ.get(CUSTOM_PROFILE_ENV)
    if configured:
        return Path(configured)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ModForgeManager" / "profiles"
    return Path.home() / ".modforge" / "profiles"


def custom_profiles(profile_dir: str | Path | None = None) -> list[GameProfile]:
    root = Path(profile_dir) if profile_dir is not None else custom_profile_dir()
    if not root.exists():
        return []
    profiles: list[GameProfile] = []
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.lower()):
        profiles.append(load_profile_file(path, trust_level="custom"))
    return profiles


def import_profile_file(path: str | Path, profile_dir: str | Path | None = None, *, force: bool = False) -> Path:
    profile = load_profile_file(path)
    report = validate_profile(profile)
    if report.has_errors:
        errors = "; ".join(issue.message for issue in report.issues if issue.status == "error")
        raise ValueError(f"Profile validation failed: {errors}")
    if not force and any(profile.id == builtin.id for builtin in builtin_profiles()):
        raise ValueError(f"Refusing to shadow built-in profile id: {profile.id}")
    root = Path(profile_dir) if profile_dir is not None else custom_profile_dir()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{profile.id}.json"
    destination.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    return destination


def builtin_profile(profile_id: str) -> GameProfile:
    candidate_path = Path(profile_id)
    if candidate_path.exists():
        return load_profile_file(candidate_path)
    for profile in all_profiles():
        if profile.id == profile_id:
            return profile
    raise KeyError(f"Unknown game profile: {profile_id}")


def validate_profile(profile: GameProfile) -> ProfileValidationReport:
    issues: list[ProfileValidationIssue] = []
    if profile.schema_version != PROFILE_SCHEMA_VERSION:
        issues.append(_issue("error", "schema_version", f"Unsupported schema_version: {profile.schema_version}"))
    if not _SAFE_PROFILE_ID.match(profile.id):
        issues.append(_issue("error", "id", f"Profile id is not safe: {profile.id}"))
    if not profile.display_name.strip():
        issues.append(_issue("error", "display_name", "display_name is required."))
    if not profile.deployment_rules:
        issues.append(_issue("error", "deployment_rules", "At least one deployment rule is required."))

    for alias, root in profile.root_aliases.items():
        if not _SAFE_PROFILE_ID.match(alias):
            issues.append(_issue("error", f"root_aliases.{alias}", f"Unsafe root alias name: {alias}"))
        if not _safe_relative_path(root, allow_dot=True):
            issues.append(_issue("error", f"root_aliases.{alias}", f"Root alias must stay relative: {root}"))

    for index, rule in enumerate(profile.deployment_rules):
        rule_name = rule.id or f"rule[{index}]"
        if not rule.patterns:
            issues.append(_issue("error", rule_name, "Rule must have at least one source pattern."))
        if not _safe_destination_root(rule.destination_root, profile.root_aliases):
            issues.append(_issue("error", rule_name, f"Unsafe destination_root: {rule.destination_root}"))
        _validate_format_pattern(rule.destination_pattern, rule_name, issues)
        if not _safe_destination_pattern(rule.destination_pattern):
            issues.append(_issue("error", rule_name, f"Unsafe destination_pattern: {rule.destination_pattern}"))
        if rule.requires_extra_confirmation or rule.safety_tier in {"runtime-file", "dll-high-risk", "high-risk"}:
            issues.append(_issue("warning", rule_name, f"High-risk rule requires review: {rule.safety_tier}"))

    for group in profile.sidecar_groups:
        if not group.id:
            issues.append(_issue("error", "sidecar_groups", "Sidecar group id is required."))
        if not group.extensions:
            issues.append(_issue("error", group.id or "sidecar_group", "Sidecar group needs extensions."))
        for extension in group.extensions:
            if not extension.startswith("."):
                issues.append(_issue("error", group.id or "sidecar_group", f"Extension must start with '.': {extension}"))

    for sample in profile.validation_samples:
        mapping = preview_profile_paths(profile, [sample.source], package_name="SampleMod")[0]
        if not mapping.destination_path:
            issues.append(_issue("error", "validation_samples", f"No rule mapped sample: {sample.source}"))
        elif mapping.destination_path != sample.expected_destination:
            issues.append(
                _issue(
                    "error",
                    "validation_samples",
                    f"{sample.source} mapped to {mapping.destination_path}, expected {sample.expected_destination}",
                )
            )

    if not any(issue.status == "error" for issue in issues):
        issues.append(_issue("ok", "profile", "Profile validation passed."))
    return ProfileValidationReport(profile_id=profile.id, issues=issues)


def preview_profile_dir(profile: GameProfile, sample_mod_dir: str | Path) -> list[ProfileMapping]:
    root = Path(sample_mod_dir)
    if root.is_file():
        return preview_profile_paths(profile, [root.name], package_name=root.stem)
    paths = [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower())
        if path.is_file()
    ]
    return preview_profile_paths(profile, paths, package_name=root.name)


def preview_profile_paths(
    profile: GameProfile,
    relative_paths: list[str],
    *,
    package_id: str = "",
    package_name: str = "",
) -> list[ProfileMapping]:
    mappings: list[ProfileMapping] = []
    for relative_path in relative_paths:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        if _ignored(normalized, profile.ignored_patterns):
            mappings.append(ProfileMapping(normalized, "", "", "ignored", action="ignored"))
            continue
        rule = profile.matching_rule(normalized)
        if rule is None:
            mappings.append(
                ProfileMapping(
                    source_path=normalized,
                    destination_path="",
                    rule_id="",
                    safety_tier="unmanaged",
                    action="unmanaged",
                    warnings=["No deployment rule matched this file."],
                )
            )
            continue
        destination = profile.destination_for_rule(
            rule,
            normalized,
            package_id=package_id,
            package_name=package_name,
        )
        warnings: list[str] = []
        if not _safe_relative_path(destination, allow_dot=False):
            warnings.append("Destination is unsafe and will be rejected before apply.")
        if rule.requires_extra_confirmation or rule.safety_tier in {"runtime-file", "dll-high-risk", "high-risk"}:
            warnings.append(f"High-risk destination requires extra confirmation: {rule.safety_tier}")
        if _protected(destination, profile.protected_paths):
            warnings.append("Destination matches a protected path.")
        mappings.append(
            ProfileMapping(
                source_path=normalized,
                destination_path=destination,
                rule_id=rule.id or ",".join(rule.patterns),
                safety_tier=rule.safety_tier,
                action=rule.mode,
                warnings=warnings,
            )
        )
    _assign_sidecar_groups(profile, mappings)
    return mappings


def _code_builtin_profiles() -> list[GameProfile]:
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
            family="unreal",
            description="Generic Unreal Engine staging profile for .pak/.ucas/.utoc ~mods workflows.",
            deployment_rules=[
                DeploymentRule(
                    id="archive-to-mods",
                    source_patterns=["*.pak", "*.ucas", "*.utoc", "**/*.pak", "**/*.ucas", "**/*.utoc"],
                    destination_root="Content/Paks/~mods",
                    destination_pattern="{filename}",
                    mode="archive_as_is",
                    safety_tier="archive",
                ),
                DeploymentRule(
                    id="extracted-or-loose-content",
                    source_pattern="**/*",
                    safety_tier="normal",
                ),
            ],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip", "unreal_pak"],
            sidecar_groups=[
                SidecarGroupRule(
                    id="unreal-sidecar",
                    extensions=[".pak", ".ucas", ".utoc"],
                    missing_behavior="warning",
                )
            ],
            validation_samples=[
                ValidationSample(
                    source="CoolOutfit_P.pak",
                    expected_destination="Content/Paks/~mods/CoolOutfit_P.pak",
                ),
                ValidationSample(
                    source="CoolOutfit_P.ucas",
                    expected_destination="Content/Paks/~mods/CoolOutfit_P.ucas",
                ),
                ValidationSample(
                    source="Content/Localization/Game/en/Game.locres",
                    expected_destination="Content/Localization/Game/en/Game.locres",
                ),
            ],
        ),
        GameProfile(
            id="sts2-mods",
            display_name="Slay the Spire 2 Mods Folder",
            deployment_rules=[
                DeploymentRule(source_pattern="*.pck", destination_root="mods", container_types=["godot_pck"]),
                DeploymentRule(
                    source_pattern="**/*.pck",
                    destination_root="mods",
                    destination_pattern="{package_name}/{relative_path}",
                    exclude_container_types=["godot_pck"],
                ),
                DeploymentRule(
                    destination_root="mods",
                    destination_pattern="{package_name}/{relative_path}",
                    exclude_container_types=["godot_pck"],
                ),
            ],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip", "godot_pck"],
        ),
        GameProfile(
            id="reframework",
            display_name="REFramework / NativePC Game Folder",
            deployment_rules=[DeploymentRule()],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="mhw-reframework",
            display_name="Monster Hunter Wilds / REFramework NativePC Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="reframework/**"),
                DeploymentRule(source_pattern="nativePC/**"),
            ],
            ignored_patterns=["**/.DS_Store", "**/Thumbs.db", "README*", "*.md"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="unity-bepinex",
            display_name="Unity BepInEx Plugin Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="BepInEx/**"),
                DeploymentRule(source_pattern="doorstop_config.ini"),
                DeploymentRule(source_pattern="winhttp.dll"),
                DeploymentRule(source_pattern="plugins/**", destination_root="BepInEx"),
                DeploymentRule(source_pattern="patchers/**", destination_root="BepInEx"),
                DeploymentRule(source_pattern="config/**", destination_root="BepInEx"),
                DeploymentRule(source_pattern="*.dll", destination_root="BepInEx/plugins"),
                DeploymentRule(source_pattern="**/*.dll", destination_root="BepInEx/plugins"),
                DeploymentRule(source_pattern="**/*", priority=100),
            ],
            ignored_patterns=["manifest.json", "icon.png", "README*", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="unity-melonloader",
            display_name="Unity MelonLoader Mod Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="Mods/**"),
                DeploymentRule(source_pattern="Plugins/**"),
                DeploymentRule(source_pattern="UserData/**"),
                DeploymentRule(source_pattern="UserLibs/**"),
                DeploymentRule(source_pattern="MelonLoader/**"),
                DeploymentRule(source_pattern="*.dll", destination_root="Mods"),
                DeploymentRule(source_pattern="**/*.dll", destination_root="Mods"),
                DeploymentRule(source_pattern="**/*", priority=100),
            ],
            ignored_patterns=["manifest.json", "icon.png", "README*", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="bethesda-data",
            display_name="Bethesda Data Folder / Script Extender Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="Data/**"),
                DeploymentRule(source_pattern="meshes/**", destination_root="Data"),
                DeploymentRule(source_pattern="textures/**", destination_root="Data"),
                DeploymentRule(source_pattern="scripts/**", destination_root="Data"),
                DeploymentRule(source_pattern="interface/**", destination_root="Data"),
                DeploymentRule(source_pattern="skse/**", destination_root="Data"),
                DeploymentRule(source_pattern="f4se/**", destination_root="Data"),
                DeploymentRule(source_pattern="sfse/**", destination_root="Data"),
                DeploymentRule(source_pattern="*.esp", destination_root="Data"),
                DeploymentRule(source_pattern="*.esm", destination_root="Data"),
                DeploymentRule(source_pattern="*.esl", destination_root="Data"),
                DeploymentRule(source_pattern="*.bsa", destination_root="Data"),
                DeploymentRule(source_pattern="**/*", priority=100),
            ],
            ignored_patterns=["fomod/**", "meta.ini", "INI Tweaks/**", ".mohidden/**", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
        GameProfile(
            id="cyberpunk-2077",
            display_name="Cyberpunk 2077 REDmod / Archive Workflow",
            deployment_rules=[
                DeploymentRule(source_pattern="archive/**"),
                DeploymentRule(source_pattern="bin/**"),
                DeploymentRule(source_pattern="engine/**"),
                DeploymentRule(source_pattern="mods/**"),
                DeploymentRule(source_pattern="r6/**"),
                DeploymentRule(source_pattern="red4ext/**"),
                DeploymentRule(source_pattern="*.archive", destination_root="archive/pc/mod"),
                DeploymentRule(source_pattern="**/*.archive", destination_root="archive/pc/mod"),
                DeploymentRule(source_pattern="**/*", priority=100),
            ],
            ignored_patterns=["manifest.json", "info.json", "README*", "**/.DS_Store", "**/Thumbs.db"],
            supported_containers=["loose_folder", "zip"],
        ),
    ]


def _json_builtin_profiles() -> list[GameProfile]:
    root = Path(__file__).resolve().parents[1] / "profiles"
    if not root.exists():
        return []
    return [load_profile_file(path, trust_level="builtin") for path in sorted(root.glob("*.json"))]


def _matches_pattern(relative_path: str, pattern: str) -> bool:
    if fnmatchcase(relative_path, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatchcase(relative_path, pattern[3:])
    return False


def _ignored(relative_path: str, patterns: list[str]) -> bool:
    return any(_matches_pattern(relative_path, pattern) for pattern in patterns)


def _issue(status: str, name: str, message: str) -> ProfileValidationIssue:
    return ProfileValidationIssue(status=status, name=name, message=message)


def _safe_destination_root(destination_root: str, root_aliases: dict[str, str]) -> bool:
    if not destination_root or destination_root in root_aliases:
        return True
    return _safe_relative_path(destination_root, allow_dot=True)


def _safe_relative_path(value: str, *, allow_dot: bool) -> bool:
    path = value.strip().replace("\\", "/")
    if not path:
        return False
    if allow_dot and path == ".":
        return True
    if path.startswith("/") or path.startswith("//") or re.match(r"^[A-Za-z]:", path):
        return False
    parts = [part for part in path.split("/") if part]
    return ".." not in parts


def _safe_destination_pattern(value: str) -> bool:
    pattern = value.replace("\\", "/")
    if pattern.startswith("/") or pattern.startswith("//") or re.match(r"^[A-Za-z]:", pattern):
        return False
    return ".." not in [part for part in pattern.split("/") if part]


def _validate_format_pattern(value: str, rule_name: str, issues: list[ProfileValidationIssue]) -> None:
    for _, field_name, _, _ in Formatter().parse(value):
        if field_name is None:
            continue
        if field_name.split(".", 1)[0].split("[", 1)[0] not in _ALLOWED_FORMAT_FIELDS:
            issues.append(_issue("error", rule_name, f"Unknown destination field: {field_name}"))


def _protected(destination: str, patterns: list[str]) -> bool:
    return any(_matches_pattern(destination, pattern) for pattern in patterns)


def _assign_sidecar_groups(profile: GameProfile, mappings: list[ProfileMapping]) -> None:
    for group in profile.sidecar_groups:
        if not group.extensions:
            continue
        by_stem: dict[str, list[ProfileMapping]] = {}
        for mapping in mappings:
            suffix = Path(mapping.source_path).suffix.lower()
            if suffix not in group.extensions:
                continue
            stem = _sidecar_stem(mapping.source_path, group)
            by_stem.setdefault(stem, []).append(mapping)
        for stem, members in by_stem.items():
            group_id = f"{group.id}:{stem}"
            present = {Path(member.source_path).suffix.lower() for member in members}
            missing = [extension for extension in group.extensions if extension not in present]
            for member in members:
                member.group_id = group_id
                if missing and group.missing_behavior == "warning":
                    member.warnings.append(f"Atomic sidecar group is incomplete: missing {', '.join(missing)}")


def _sidecar_stem(source_path: str, group: SidecarGroupRule) -> str:
    normalized = source_path.replace("\\", "/")
    if group.stem_regex:
        match = re.match(group.stem_regex, Path(normalized).name)
        if match:
            if "stem" in match.groupdict():
                return match.group("stem").casefold()
            if match.groups():
                return match.group(1).casefold()
    return str(Path(normalized).with_suffix("")).casefold()
