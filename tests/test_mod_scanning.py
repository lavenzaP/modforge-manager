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

    def test_scan_mhw_reframework_fixture_order_and_files(self) -> None:
        packages = scan_mods(FIXTURES / "mhw_reframework_mods")

        self.assertEqual(
            [(package.priority, package.enabled, package.name) for package in packages],
            [
                (0, True, "BaseScript"),
                (1, True, "LooseNotes"),
                (2, True, "NativeSword"),
                (3, True, "NativeSwordPatch"),
            ],
        )
        self.assertEqual(
            {
                package.name: [file.relative_path for file in package.files]
                for package in packages
            },
            {
                "BaseScript": [
                    "README.md",
                    "reframework/autorun/base_script.lua",
                    "reframework/data/BaseScript/settings.json",
                ],
                "LooseNotes": ["docs/install.txt"],
                "NativeSword": [
                    "nativePC/wp/swo/swo001/mod/swo001.mod3",
                    "nativePC/wp/swo/swo001/mod/swo001.mrl3",
                ],
                "NativeSwordPatch": [
                    "nativePC/wp/swo/swo001/mod/swo001.mod3",
                    "reframework/autorun/sword_patch.lua",
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
