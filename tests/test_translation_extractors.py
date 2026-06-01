from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.translation.csv_extractor import extract_csv_strings
from modforge.translation.exporter import extract_strings, write_entries_csv
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


if __name__ == "__main__":
    unittest.main()
