"""Conflict summary helpers for the optional Qt UI."""

from __future__ import annotations

from modforge.core.conflict_detector import Conflict


def format_conflicts(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return "No conflicts detected."
    lines = ["Conflicts:", ""]
    for conflict in conflicts:
        lines.append(f"- {conflict.destination_path}")
        lines.append(f"  winner: {conflict.winning_mod}")
        lines.append(f"  mods: {', '.join(conflict.mods)}")
    return "\n".join(lines)
