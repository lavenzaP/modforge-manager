from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_game, apply_to_staging, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject


class DeployerTests(unittest.TestCase):
    def test_apply_to_staging_copies_winners_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / "staging"
            (mods / "A" / "config").mkdir(parents=True)
            (mods / "B" / "config").mkdir(parents=True)
            game.mkdir()
            (mods / "A" / "config" / "settings.json").write_text("a", encoding="utf-8")
            (mods / "B" / "config" / "settings.json").write_text("b", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)

            self.assertEqual((staging / "config" / "settings.json").read_text(encoding="utf-8"), "b")
            self.assertEqual(manifest.skipped_files, ["config/settings.json"])
            self.assertTrue((staging / ".modforge-install-manifest.json").exists())
            self.assertFalse((game / "config" / "settings.json").exists())

    def test_apply_to_staging_extracts_zip_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / "staging"
            mods.mkdir()
            game.mkdir()
            with ZipFile(mods / "ZipMod.zip", "w") as zip_file:
                zip_file.writestr("textures/icon.txt", "icon")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)

            self.assertEqual((staging / "textures" / "icon.txt").read_text(encoding="utf-8"), "icon")
            self.assertEqual(manifest.copied_files, ["textures/icon.txt"])

    def test_apply_to_game_backs_up_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            (mods / "Patch" / "config").mkdir(parents=True)
            (mods / "Patch" / "textures").mkdir(parents=True)
            (game / "config").mkdir(parents=True)
            (mods / "Patch" / "config" / "settings.json").write_text("patched", encoding="utf-8")
            (mods / "Patch" / "textures" / "new.txt").write_text("new", encoding="utf-8")
            (game / "config" / "settings.json").write_text("original", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = staging.parent / "manifests" / f"{manifest.manifest_id}.json"

            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "patched")
            self.assertEqual((game / "textures" / "new.txt").read_text(encoding="utf-8"), "new")
            self.assertEqual(manifest.overwritten_files, ["config/settings.json"])
            self.assertEqual(manifest.copied_files, ["textures/new.txt"])
            self.assertTrue(manifest_path.exists())

            restored = restore_manifest(manifest_path)

            self.assertTrue(restored.restored_at)
            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "original")
            self.assertFalse((game / "textures" / "new.txt").exists())

    def test_restore_manifest_can_restore_selected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            (mods / "Patch" / "config").mkdir(parents=True)
            (mods / "Patch" / "textures").mkdir(parents=True)
            (game / "config").mkdir(parents=True)
            (mods / "Patch" / "config" / "settings.json").write_text("patched", encoding="utf-8")
            (mods / "Patch" / "textures" / "new.txt").write_text("new", encoding="utf-8")
            (game / "config" / "settings.json").write_text("original", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = staging.parent / "manifests" / f"{manifest.manifest_id}.json"

            restore_manifest(manifest_path, [r"config\settings.json"])

            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "original")
            self.assertEqual((game / "textures" / "new.txt").read_text(encoding="utf-8"), "new")

            restore_manifest(manifest_path, ["textures/new.txt"])

            self.assertFalse((game / "textures" / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
