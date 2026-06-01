"""Translation validation helpers."""

from __future__ import annotations

from modforge.translation.extractor_base import TranslationEntry


def missing_targets(entries: list[TranslationEntry]) -> list[TranslationEntry]:
    return [entry for entry in entries if not entry.target.strip()]
