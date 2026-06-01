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

    grouped: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for destination_path, mod_name, priority in entries:
        grouped[conflict_path_key(destination_path)].append((destination_path, mod_name, priority))

    conflicts: list[Conflict] = []
    for mods in grouped.values():
        unique_mods = {name for _path, name, _priority in mods}
        if len(unique_mods) <= 1:
            continue
        destination_path = sorted({path for path, _name, _priority in mods}, key=_path_sort_key)[0]
        winner = max(mods, key=lambda item: (item[2], item[1].casefold(), item[1]))[1]
        conflicts.append(
            Conflict(
                destination_path=destination_path,
                mods=[
                    name
                    for _path, name, _priority in sorted(
                        mods,
                        key=lambda item: (item[2], item[1].casefold(), item[1]),
                    )
                ],
                winning_mod=winner,
            )
        )
    return sorted(conflicts, key=lambda conflict: conflict_path_key(conflict.destination_path))


def conflict_path_key(destination_path: str) -> str:
    """Return the Windows-safe comparison key for a deployment destination."""

    return destination_path.replace("\\", "/").casefold()


def _path_sort_key(destination_path: str) -> tuple[str, str]:
    return (destination_path.casefold(), destination_path)
