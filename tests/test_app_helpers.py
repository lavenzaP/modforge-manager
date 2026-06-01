from __future__ import annotations

from pathlib import Path
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.app import ModForgeApp
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.mod_package import ModFile, ModPackage
from modforge.core.mod_project import ModProject
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

    def test_restore_preview_summary_shows_safe_action_counts_and_warnings(self) -> None:
        summary = ModForgeApp.restore_preview_summary(
            {
                "manifest_id": "demo",
                "target_root": "C:/Game",
                "can_restore": False,
                "restore_from_backup": 1,
                "delete_copied_files": 1,
                "records": [
                    {
                        "destination_path": "config/settings.json",
                        "action": "restore-backup",
                    },
                    {
                        "destination_path": "textures/new.txt",
                        "action": "remove-created-file",
                    },
                ],
                "warnings": ["Backup is missing: C:/Backups/config/settings.json"],
            }
        )

        self.assertIn("Can restore: no", summary)
        self.assertIn("Will restore backups: 1", summary)
        self.assertIn("Will delete newly copied files: 1", summary)
        self.assertIn("WARNING: Backup is missing", summary)

    def test_project_health_summary_includes_audit_and_manifest_state(self) -> None:
        summary = ModForgeApp.project_health_summary(
            {
                "project_name": "Demo",
                "issues": [
                    {
                        "name": "mods-dir",
                        "status": "error",
                        "message": "Directory is unavailable",
                    }
                ],
            },
            [
                {
                    "manifest_id": "abc",
                    "target": "game",
                    "can_restore": False,
                    "restorable": 2,
                    "warnings": ["Backup is missing"],
                }
            ],
        )

        self.assertIn("Project health: Demo", summary)
        self.assertIn("ERROR   mods-dir", summary)
        self.assertIn("abc (game, blocked, records=2)", summary)
        self.assertIn("WARNING: Backup is missing", summary)

    def test_sorted_packages_supports_table_columns(self) -> None:
        packages = [
            ModPackage("b", "Beta", Path("Beta"), True, 10, "zip", [ModFile("b.txt", 1)], ["warn"]),
            ModPackage("a", "Alpha", Path("Alpha"), False, 1, "loose_folder", [], []),
        ]

        self.assertEqual(
            [package.name for package in ModForgeApp.sorted_packages(packages, "warnings", reverse=True)],
            ["Beta", "Alpha"],
        )
        self.assertEqual(
            [package.name for package in ModForgeApp.sorted_packages(packages, "name")],
            ["Alpha", "Beta"],
        )

    def test_scan_summary_includes_warnings_and_extracted_path(self) -> None:
        project = ModProject.create("Demo", Path("C:/Game"), Path("C:/Mods"), Path("C:/Mods/.modforge/staging"))
        package = ModPackage(
            "archive",
            "Archive",
            Path("Archive.pak"),
            True,
            0,
            "unreal_pak",
            [ModFile("Content/A.uasset", 5)],
            ["External extraction produced no files."],
            Path("C:/Mods/.modforge/extracted/unreal_pak/archive"),
        )

        summary = ModForgeApp.scan_summary(project, [package])

        self.assertIn("Archive (unreal_pak, 1 files)", summary)
        self.assertIn(f"extracted: {package.extracted_path}", summary)
        self.assertIn("warning: External extraction produced no files.", summary)

    def test_manifest_record_rows_excludes_skipped_records(self) -> None:
        manifest = InstallManifest(
            manifest_id="demo",
            records=[
                InstallRecord("config/settings.json", "Patch", "config/settings.json", "overwritten", "backup"),
                InstallRecord("textures/new.txt", "Patch", "textures/new.txt", "copied", ""),
                InstallRecord("config/settings.json", "Old", "config/settings.json", "skipped", ""),
            ],
        )

        rows = ModForgeApp.manifest_record_rows(manifest)

        self.assertEqual(
            rows,
            [
                ("config/settings.json", "overwritten", "Patch", "yes"),
                ("textures/new.txt", "copied", "Patch", "no"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
