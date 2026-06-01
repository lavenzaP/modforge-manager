from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.project_portability import audit_project, export_project, import_project
from modforge.core.mod_project import ModProject


class ProjectPortabilityTests(unittest.TestCase):
    def test_project_export_import_preserves_config_without_real_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            export_file = root / "export.json"
            import_dir = root / "imported"
            game.mkdir()
            (mods / "Example").mkdir(parents=True)
            (mods / "Example" / "file.txt").write_text("real mod content", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / ".modforge" / "staging", game_profile="sts2-mods")
            project.set_mod_enabled("example", False)

            payload = export_project(project, export_file)
            imported = import_project(export_file, import_dir)

            self.assertTrue(export_file.exists())
            self.assertFalse(payload["includes"]["game_files"])
            self.assertFalse(payload["includes"]["mod_files"])
            self.assertFalse(payload["includes"]["backup_files"])
            self.assertFalse((import_dir / "mods" / "Example" / "file.txt").exists())
            self.assertEqual(imported.name, "Demo")
            self.assertEqual(imported.game_profile.id, "sts2-mods")
            saved = json.loads((import_dir / "modforge.project.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["staging_dir"], str(import_dir / ".modforge" / "staging"))
            self.assertEqual(saved["user_profiles"][0]["disabled_mod_ids"], ["example"])

    def test_project_audit_reports_missing_required_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = ModProject.create("Demo", root / "missing-game", root / "missing-mods", root / ".modforge" / "staging")

            report = audit_project(project)
            issues = {issue.name: issue for issue in report.issues}

            self.assertEqual(issues["game-root"].status, "warning")
            self.assertEqual(issues["mods-dir"].status, "error")
            self.assertTrue(report.has_errors)


if __name__ == "__main__":
    unittest.main()
