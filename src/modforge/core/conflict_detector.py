"""Conflict detection for deployment destinations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Conflict:
    destination_path: str
    mods: list[str]
    winning_mod: str

    def to_dict(self) -> dict[str, object]:
        return {
            "destination_path": self.destination_path,
            "mods": self.mods,
            "winning_mod": self.winning_mod,
        }


def detect_conflicts(entries: list[tuple[str, str, int]]) -> list[Conflict]:
    """Detect conflicts from `(destination_path, mod_name, priority)` entries."""

    grouped: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for destination_path, mod_name, priority in entries:
        grouped[destination_path].append((mod_name, priority))

    conflicts: list[Conflict] = []
    for destination_path, mods in grouped.items():
        unique_mods = {name for name, _priority in mods}
        if len(unique_mods) <= 1:
            continue
        winner = max(mods, key=lambda item: item[1])[0]
        conflicts.append(
            Conflict(
                destination_path=destination_path,
                mods=[name for name, _priority in sorted(mods, key=lambda item: item[1])],
                winning_mod=winner,
            )
        )
    return sorted(conflicts, key=lambda conflict: conflict.destination_path)
