"""Project file model."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from modforge.core.game_profile import GameProfile, builtin_profile
from modforge.core.paths import normalize_path
from modforge.core.user_profile import UserProfile


@dataclass(slots=True)
class ModProject:
    name: str
    game_root: Path
    mods_dir: Path
    staging_dir: Path
    game_profile: GameProfile
    active_user_profile: str
    user_profiles: list[UserProfile]
    external_tools: dict[str, str]

    @classmethod
    def create(
        cls,
        name: str,
        game_root: str | Path,
        mods_dir: str | Path,
        staging_dir: str | Path,
        game_profile: GameProfile | str | None = None,
    ) -> "ModProject":
        profile = (
            builtin_profile(game_profile)
            if isinstance(game_profile, str)
            else game_profile
            if game_profile is not None
            else GameProfile.generic()
        )
        return cls(
            name=name,
            game_root=normalize_path(game_root),
            mods_dir=normalize_path(mods_dir),
            staging_dir=normalize_path(staging_dir),
            game_profile=profile,
            active_user_profile="default",
            user_profiles=[UserProfile()],
            external_tools={},
        )

    @classmethod
    def load(cls, path: Path) -> "ModProject":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            name=str(payload["name"]),
            game_root=normalize_path(payload["game_root"]),
            mods_dir=normalize_path(payload["mods_dir"]),
            staging_dir=normalize_path(payload["staging_dir"]),
            game_profile=GameProfile.from_dict(payload["game_profile"]),
            active_user_profile=str(payload.get("active_user_profile", "default")),
            user_profiles=[
                UserProfile.from_dict(item)
                for item in payload.get("user_profiles", [{"id": "default", "name": "Default"}])
            ],
            external_tools=dict(payload.get("external_tools", {})),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def active_profile(self) -> UserProfile:
        for profile in self.user_profiles:
            if profile.id == self.active_user_profile:
                return profile
        profile = UserProfile(id=self.active_user_profile, name=self.active_user_profile)
        self.user_profiles.append(profile)
        return profile

    def set_mod_enabled(self, mod_id: str, enabled: bool) -> None:
        self.active_profile().set_enabled(mod_id, enabled)

    def set_priority_order(self, ordered_mod_ids: list[str]) -> None:
        self.active_profile().set_priority_order(ordered_mod_ids)

    def set_tool_path(self, tool_id: str, tool_path: str) -> None:
        if tool_path:
            self.external_tools[tool_id] = tool_path
        else:
            self.external_tools.pop(tool_id, None)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "game_root": str(self.game_root),
            "mods_dir": str(self.mods_dir),
            "staging_dir": str(self.staging_dir),
            "game_profile": self.game_profile.to_dict(),
            "active_user_profile": self.active_user_profile,
            "user_profiles": [profile.to_dict() for profile in self.user_profiles],
            "external_tools": self.external_tools,
        }
