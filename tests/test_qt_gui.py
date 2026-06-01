from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.conflict_detector import Conflict
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.mod_package import ModFile, ModPackage
from modforge.core.mod_project import ModProject
from modforge.gui import main_window
from modforge.gui.models import build_mod_rows, create_mod_table_model
from modforge.gui.qt_compat import pyside6_status
from modforge.gui.widgets import format_conflicts, format_project_summary
from modforge.tools.checker import ToolCheck


class QtGuiTests(unittest.TestCase):
    def test_build_mod_rows_sorts_by_priority_then_name(self) -> None:
        packages = [
            ModPackage("z", "Zeta", Path("Zeta"), True, 2, "zip", [], []),
            ModPackage(
                "a",
                "Alpha",
                Path("Alpha"),
                False,
                1,
                "loose_folder",
                [ModFile("a", 1)],
                ["warn"],
            ),
        ]

        rows = build_mod_rows(packages)

        self.assertEqual([row.name for row in rows], ["Alpha", "Zeta"])
        self.assertEqual(rows[0].display_values(), ["Alpha", "no", "1", "loose_folder", "1", "1"])

    def test_qt_table_model_is_import_gated(self) -> None:
        available, _message = pyside6_status()
        package = ModPackage("demo", "Demo", Path("Demo"), True, 0, "loose_folder", [], [])

        if available:
            model = create_mod_table_model([package])
            self.assertEqual(model.rowCount(), 1)
            self.assertEqual(model.columnCount(), 6)
        else:
            with self.assertRaisesRegex(RuntimeError, "PySide6"):
                create_mod_table_model([package])

    def test_qt_dependency_check_never_opens_a_window(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main_window.main(["--check-dependency"])

        available, _message = pyside6_status()
        self.assertEqual(exit_code, 0 if available else 1)
        self.assertIn("PySide6", stdout.getvalue() + stderr.getvalue())

    def test_qt_summary_formatters_match_core_results(self) -> None:
        project = ModProject.create("Demo", Path("C:/Game"), Path("C:/Mods"), Path("C:/Staging"))
        package = ModPackage(
            "demo",
            "Demo",
            Path("Demo"),
            True,
            0,
            "loose_folder",
            [ModFile("config.json", 2)],
            ["warning"],
        )
        manifest = InstallManifest(
            manifest_id="demo",
            copied_files=["config.json"],
            overwritten_files=["old.json"],
            backups=["old.json"],
            records=[
                InstallRecord("config.json", "Demo", "config.json", "copied", ""),
                InstallRecord("old.json", "Demo", "old.json", "overwritten", "backup"),
            ],
        )
        checks = [ToolCheck("unreal_pak", "UnrealPak", "", False, "UnrealPak is missing.")]
        scan_summary = main_window.format_scan_summary(project, [package])

        self.assertIn("Demo (loose_folder, 1 files)", scan_summary)
        self.assertIn("profile: generic-folder", format_project_summary(project))
        self.assertIn("MISSING unreal_pak", main_window.format_tool_checks(checks))
        self.assertIn("Backups: 1", main_window.format_manifest_summary(manifest))
        self.assertIn(
            "winner: Demo",
            format_conflicts([Conflict("config.json", ["Base", "Demo"], "Demo")]),
        )


if __name__ == "__main__":
    unittest.main()
