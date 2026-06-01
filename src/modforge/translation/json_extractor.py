"""Simple JSON string extractor."""

from __future__ import annotations

import json
from pathlib import Path

from modforge.translation.extractor_base import TranslationEntry


def extract_json_strings(path: Path) -> list[TranslationEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries: list[TranslationEntry] = []

    def walk(value: object, prefix: str) -> None:
        if isinstance(value, str) and value.strip():
            entries.append(
                TranslationEntry(
                    key=prefix,
                    source=value,
                    file=str(path),
                    extractor="json",
                )
            )
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{prefix}.{key}" if prefix else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{prefix}[{index}]")

    walk(payload, "")
    return entries
