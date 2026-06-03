from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.translation.csv_extractor import extract_csv_strings
from modforge.translation.exporter import extract_strings, write_entries_csv
from modforge.translation.inventory import build_translation_inventory
from modforge.translation.json_extractor import extract_json_strings


class TranslationExtractorTests(unittest.TestCase):
    def test_json_and_csv_extractors_return_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            json_path = root / "strings.json"
            csv_path = root / "strings.csv"
            json_path.write_text('{"menu": {"start": "Start Game"}}', encoding="utf-8")
            csv_path.write_text("key,text\nhello,Hello\n", encoding="utf-8")

            self.assertEqual(extract_json_strings(json_path)[0].source, "Start Game")
            self.assertEqual(extract_csv_strings(csv_path)[0].source, "hello")
            entries = extract_strings(root)
            output = root / "extracted.csv"
            write_entries_csv(entries, output)
            self.assertTrue(output.exists())

    def test_inventory_classifies_unreal_translation_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Content" / "Localization" / "Game" / "en").mkdir(parents=True)
            (root / "Content" / "Data").mkdir(parents=True)
            (root / "Content" / "Art").mkdir(parents=True)
            (root / "Content" / "Paks" / "~mods").mkdir(parents=True)
            (root / ".modforge-install-manifest.json").write_text('{"records": []}', encoding="utf-8")
            (root / "Content" / "Localization" / "Game" / "en" / "Game.locres").write_bytes(b"locres")
            (root / "Content" / "Data" / "menu.json").write_text('{"start": "Start"}', encoding="utf-8")
            (root / "Content" / "Data" / "dialog.csv").write_text("key,text\nhello,Hello\n", encoding="utf-8")
            (root / "Content" / "Art" / "icon.uasset").write_bytes(b"asset")
            (root / "Content" / "Paks" / "~mods" / "CoolOutfit_P.pak").write_bytes(b"pak")

            report = build_translation_inventory(
                root,
                project_name="Unreal Demo",
                profile_id="unreal-pak",
                profile_family="unreal",
            )
            payload = report.to_dict()

            self.assertEqual(payload["summary"]["extractable"], 2)
            self.assertEqual(payload["summary"]["tool_required"], 1)
            self.assertEqual(payload["summary"]["archive_not_inspected"], 1)
            self.assertEqual(payload["summary"]["binary_asset"], 1)
            self.assertFalse(any(
                candidate["relative_path"] == ".modforge-install-manifest.json"
                for candidate in payload["candidates"]
            ))


if __name__ == "__main__":
    unittest.main()
