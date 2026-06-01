from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.containers.detector import detect_container


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


if __name__ == "__main__":
    unittest.main()
