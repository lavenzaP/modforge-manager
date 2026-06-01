"""Translation patch builder placeholder."""

from __future__ import annotations

from modforge.translation.extractor_base import TranslationEntry


def build_patch_summary(entries: list[TranslationEntry]) -> dict[str, int]:
    return {
        "entries": len(entries),
        "translated": sum(1 for entry in entries if entry.target.strip()),
        "missing": sum(1 for entry in entries if not entry.target.strip()),
    }
