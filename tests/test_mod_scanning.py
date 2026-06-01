from __future__ import annotations

from pathlib import Path
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.mod_package import scan_mods


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ModScanningTests(unittest.TestCase):
    def test_scan_loose_mod_folders(self) -> None:
        packages = scan_mods(FIXTURES / "fake_mods")

        self.assertEqual([package.name for package in packages], ["BetterUI", "Overhaul"])
        self.assertEqual(packages[0].detected_type, "loose_folder")
        self.assertIn("config/settings.json", [file.relative_path for file in packages[0].files])


if __name__ == "__main__":
    unittest.main()
