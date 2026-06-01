from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.containers.detector import detect_container
from modforge.containers.zip_adapter import list_files


class ContainerDetectionTests(unittest.TestCase):
    def test_detects_loose_folder_and_known_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            loose = root / "LooseMod"
            loose.mkdir()
            archive = root / "Test.pak"
            archive.write_bytes(b"not a real pak")

            self.assertEqual(detect_container(loose).container_type, "loose_folder")
            self.assertEqual(detect_container(archive).container_type, "unreal_pak")
            self.assertFalse(detect_container(archive).supported)

    def test_zip_adapter_lists_safe_members(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "ArchiveMod.zip"
            with ZipFile(archive, "w") as zip_file:
                zip_file.writestr("config/settings.json", "{}")
                zip_file.writestr("../unsafe.txt", "bad")
                zip_file.writestr("/absolute.txt", "bad")
                zip_file.writestr("C:/absolute.txt", "bad")

            info = detect_container(archive)
            files, warnings = list_files(archive)

            self.assertEqual(info.container_type, "zip")
            self.assertTrue(info.supported)
            self.assertEqual(files, [("config/settings.json", 2)])
            self.assertEqual(len(warnings), 3)


if __name__ == "__main__":
    unittest.main()
