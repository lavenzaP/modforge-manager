"""Project file model."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from modforge.core.game_profile import GameProfile
from modforge.core.paths import normalize_path


@dataclass(slots=True)
class ModProject:
    name: str
    game_root: Path
    mods_dir: Path
    staging_dir: Path
    game_profile: GameProfile

    @classmethod
    def create(
        cls,
        name: str,
        game_root: str | Path,
        mods_dir: str | Path,
        staging_dir: str | Path,
    ) -> "ModProject":
        return cls(
            name=name,
            game_root=normalize_path(game_root),
            mods_dir=normalize_path(mods_dir),
            staging_dir=normalize_path(staging_dir),
            game_profile=GameProfile.generic(),
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
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "game_root": str(self.game_root),
            "mods_dir": str(self.mods_dir),
            "staging_dir": str(self.staging_dir),
            "game_profile": self.game_profile.to_dict(),
        }
