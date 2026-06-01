"""Base extraction result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationEntry:
    key: str
    source: str
    target: str = ""
    file: str = ""
    context: str = ""
    extractor: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "source": self.source,
            "target": self.target,
            "file": self.file,
            "context": self.context,
            "extractor": self.extractor,
            "notes": self.notes,
        }
