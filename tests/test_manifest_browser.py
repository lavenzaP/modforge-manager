from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_game
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.manifest_browser import find_manifest, latest_manifest_summary, list_manifest_summaries
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject


class ManifestBrowserTests(unittest.TestCase):
    def test_manifest_list_latest_and_find_use_restore_availability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            staging = root / ".modforge" / "staging"
            (mods / "Patch").mkdir(parents=True)
            game.mkdir()
            (mods / "Patch" / "new.txt").write_text("new", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)

            summaries = list_manifest_summaries(project)
            latest = latest_manifest_summary(project)

            self.assertEqual(len(summaries), 1)
            self.assertIsNotNone(latest)
            self.assertEqual(latest.manifest_id, manifest.manifest_id)
            self.assertTrue(latest.can_restore)
            self.assertEqual(latest.restorable, 1)
            self.assertEqual(find_manifest(project, manifest.manifest_id[:8]).name, f"{manifest.manifest_id}.json")

    def test_manifest_summary_reports_missing_backup_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            staging = root / ".modforge" / "staging"
            (mods / "Patch").mkdir(parents=True)
            game.mkdir()
            (game / "settings.txt").write_text("original", encoding="utf-8")
            (mods / "Patch" / "settings.txt").write_text("patched", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            Path(manifest.records[0].backup_path).unlink()

            summary = latest_manifest_summary(project)

            self.assertIsNotNone(summary)
            self.assertFalse(summary.can_restore)
            self.assertTrue(any("Backup is missing" in warning for warning in summary.warnings))

    def test_manifest_list_reports_malformed_json_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = ModProject.create(
                "Demo",
                root / "game",
                root / "mods",
                root / ".modforge" / "staging",
            )
            manifest_dir = project.staging_dir.parent / "manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "broken.json").write_text("{not json", encoding="utf-8")

            summaries = list_manifest_summaries(project)

            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0].target, "invalid")
            self.assertFalse(summaries[0].can_restore)


if __name__ == "__main__":
    unittest.main()
