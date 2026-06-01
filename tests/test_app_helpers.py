from __future__ import annotations

import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.app import ModForgeApp
from modforge.tools.checker import ToolCheck


class AppHelperTests(unittest.TestCase):
    def test_manifest_summary_counts_fields(self) -> None:
        summary = ModForgeApp.manifest_summary(
            {
                "manifest_id": "demo",
                "target": "game",
                "copied_files": ["a"],
                "overwritten_files": ["b"],
                "skipped_files": [],
                "backups": ["b"],
                "target_root": "C:/Game",
                "backup_dir": "C:/Backups/demo",
            }
        )

        self.assertIn("Manifest: demo", summary)
        self.assertIn("Copied: 1", summary)
        self.assertIn("Backups: 1", summary)

    def test_tool_checks_summary_shows_ok_and_missing(self) -> None:
        summary = ModForgeApp.tool_checks_summary(
            [
                ToolCheck("seven_zip", "7-Zip", "C:/Tools/7z.exe", True),
                ToolCheck("unreal_pak", "UnrealPak", "", False, "UnrealPak is missing."),
            ]
        )

        self.assertIn("OK      seven_zip (7-Zip)", summary)
        self.assertIn("MISSING unreal_pak (UnrealPak)", summary)
        self.assertIn("UnrealPak is missing.", summary)


if __name__ == "__main__":
    unittest.main()
