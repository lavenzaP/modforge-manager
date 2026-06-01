from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.cli import main
from modforge.core.mod_project import ModProject
from modforge.doctor import format_doctor_report, run_doctor


class DoctorTests(unittest.TestCase):
    def test_doctor_warns_when_project_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = run_doctor(Path(temp) / "missing.project.json")

            self.assertFalse(report.has_errors)
            self.assertTrue(report.has_warnings)
            self.assertEqual(report.exit_code(), 0)
            self.assertEqual(report.exit_code(strict=True), 1)
            self.assertIn("project-file", format_doctor_report(report))

    def test_doctor_checks_existing_project_without_running_external_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            game.mkdir()
            (mods / "Example").mkdir(parents=True)
            (mods / "Example" / "config.json").write_text("{}", encoding="utf-8")
            (mods / "ShouldNotExtract.pak").write_bytes(b"not a real pak")
            sentinel = root / "external-tool-ran.txt"
            script = (
                "from pathlib import Path; "
                f"Path({str(sentinel)!r}).write_text('ran', encoding='utf-8')"
            )
            project = ModProject.create("Demo", game, mods, root / ".modforge" / "staging")
            project.set_tool_path(
                "unreal_pak",
                f'"{sys.executable}" -c "{script}" {{archive}} {{output}}',
            )
            project.save(project_file)

            report = run_doctor(project_file)

            statuses = {check.name: check.status for check in report.checks}
            self.assertEqual(statuses["project-file"], "ok")
            self.assertEqual(statuses["game-root"], "ok")
            self.assertEqual(statuses["mods-dir"], "ok")
            self.assertEqual(statuses["tool:unreal_pak"], "ok")
            self.assertEqual(statuses["scan"], "ok")
            self.assertFalse(sentinel.exists())

    def test_doctor_reports_malformed_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project_file = root / "modforge.project.json"
            project_file.write_text(
                json.dumps(
                    {
                        "name": "Broken",
                        "game_root": str(root / "game"),
                        "mods_dir": str(root / "mods"),
                        "staging_dir": str(root / ".modforge" / "staging"),
                        "game_profile": None,
                    }
                ),
                encoding="utf-8",
            )

            report = run_doctor(project_file)

            statuses = {check.name: check.status for check in report.checks}
            self.assertEqual(statuses["project-file"], "error")
            self.assertEqual(report.exit_code(), 1)

    def test_doctor_skips_scan_when_mods_dir_is_not_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods_file = root / "mods.txt"
            project_file = root / "modforge.project.json"
            game.mkdir()
            mods_file.write_text("", encoding="utf-8")
            project = ModProject.create("Demo", game, mods_file, root / ".modforge" / "staging")
            project.save(project_file)

            report = run_doctor(project_file)

            checks = {check.name: check for check in report.checks}
            self.assertEqual(checks["mods-dir"].status, "error")
            self.assertEqual(checks["scan"].status, "error")
            self.assertIn("Skipped", checks["scan"].message)

    def test_cli_doctor_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    ["doctor", "--project-file", str(Path(temp) / "missing.json"), "--json"]
                )

            payload = json.loads(output.getvalue())
            checks = {check["name"]: check for check in payload["checks"]}
            self.assertEqual(exit_code, 0)
            self.assertEqual(checks["python"]["status"], "ok")
            self.assertEqual(checks["project-file"]["status"], "warning")

    def test_doctor_includes_project_audit_and_health_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            health_report = root / "health.md"
            game.mkdir()
            project = ModProject.create("Demo", game, mods, root / ".modforge" / "staging")
            project.save(project_file)

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "doctor",
                        "--project-file",
                        str(project_file),
                        "--health-report",
                        str(health_report),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("audit:mods-dir", output.getvalue())
            self.assertTrue(health_report.exists())


if __name__ == "__main__":
    unittest.main()
