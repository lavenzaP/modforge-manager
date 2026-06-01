"""Simple CSV string extractor."""

from __future__ import annotations

import csv
from pathlib import Path

from modforge.translation.extractor_base import TranslationEntry


def extract_csv_strings(path: Path) -> list[TranslationEntry]:
    entries: list[TranslationEntry] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, row in enumerate(reader):
            for key, value in row.items():
                if value and value.strip():
                    entries.append(
                        TranslationEntry(
                            key=f"{row_index}.{key}",
                            source=value,
                            file=str(path),
                            extractor="csv",
                        )
                    )
    return entries
