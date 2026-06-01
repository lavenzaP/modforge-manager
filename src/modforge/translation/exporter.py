"""Translation extraction/export facade."""

from __future__ import annotations

import csv
from pathlib import Path

from modforge.translation.csv_extractor import extract_csv_strings
from modforge.translation.extractor_base import TranslationEntry
from modforge.translation.json_extractor import extract_json_strings


def extract_strings(root: Path) -> list[TranslationEntry]:
    entries: list[TranslationEntry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".json":
            entries.extend(extract_json_strings(path))
        elif path.suffix.lower() == ".csv":
            entries.extend(extract_csv_strings(path))
        elif path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                entries.append(
                    TranslationEntry(
                        key=path.stem,
                        source=text,
                        file=str(path),
                        extractor="txt",
                    )
                )
    return entries


def write_entries_csv(entries: list[TranslationEntry], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["key", "source", "target", "file", "context", "extractor", "notes"],
        )
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry.to_dict())
