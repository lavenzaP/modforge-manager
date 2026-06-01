from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

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

    def test_scan_zip_mod_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            mods = Path(temp) / "mods"
            mods.mkdir()
            with ZipFile(mods / "ZipMod.zip", "w") as zip_file:
                zip_file.writestr("textures/icon.txt", "icon")

            packages = scan_mods(mods)

            self.assertEqual(packages[0].name, "ZipMod")
            self.assertEqual(packages[0].detected_type, "zip")
            self.assertEqual(packages[0].files[0].relative_path, "textures/icon.txt")


if __name__ == "__main__":
    unittest.main()
