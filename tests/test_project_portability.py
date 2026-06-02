from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.project_portability import audit_project, export_project, import_project
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.manifest_browser import manifest_dir_for_project
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
            project.set_priority_order(["example"])
            project.external_tools["godot_pck"] = r"C:\Tools\godotpcktool.exe {archive}"
            manifest = InstallManifest(
                manifest_id="metadata-only",
                target="game",
                target_root=str(game),
                records=[
                    InstallRecord(
                        destination_path="mods/Example/file.txt",
                        source_mod="Example",
                        source_path="file.txt",
                        status="copied",
                    )
                ],
            )
            manifest_dir_for_project(project).mkdir(parents=True)
            manifest.save(manifest_dir_for_project(project) / "metadata-only.json")

            payload = export_project(project, export_file)
            imported = import_project(export_file, import_dir)

            self.assertTrue(export_file.exists())
            self.assertFalse(payload["includes"]["game_files"])
            self.assertFalse(payload["includes"]["mod_files"])
            self.assertFalse(payload["includes"]["backup_files"])
            self.assertTrue(payload["includes"]["manifests"])
            self.assertEqual(payload["manifests"][0]["manifest_id"], "metadata-only")
            self.assertFalse((import_dir / "mods" / "Example" / "file.txt").exists())
            self.assertEqual(imported.name, "Demo")
            self.assertEqual(imported.game_profile.id, "sts2-mods")
            self.assertEqual(imported.external_tools["godot_pck"], r"C:\Tools\godotpcktool.exe {archive}")
            saved = json.loads((import_dir / "modforge.project.json").read_text(encoding="utf-8"))
            self.assertEqual(
                Path(saved["staging_dir"]).resolve(strict=False),
                (import_dir / ".modforge" / "staging").resolve(strict=False),
            )
            self.assertEqual(saved["user_profiles"][0]["disabled_mod_ids"], ["example"])
            self.assertEqual(saved["user_profiles"][0]["mod_priority_order"], ["example"])
            self.assertTrue((manifest_dir_for_project(imported) / "metadata-only.json").exists())

            no_manifest_export = root / "export-no-manifests.json"
            no_manifest_payload = export_project(project, no_manifest_export, include_manifests=False)

            self.assertFalse(no_manifest_payload["includes"]["manifests"])
            self.assertNotIn("manifests", no_manifest_payload)

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
