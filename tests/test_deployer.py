from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_game, apply_to_staging, preview_restore_manifest, restore_manifest
from modforge.core.deployment_plan import DeploymentOperation, DeploymentPlan, build_deployment_plan
from modforge.core.manifest import InstallManifest, InstallRecord
from modforge.core.mod_package import ModFile, ModPackage, scan_mods
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

    def test_apply_to_staging_respects_disabled_mods(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / "staging"
            (mods / "BetterUI" / "config").mkdir(parents=True)
            (mods / "Overhaul" / "config").mkdir(parents=True)
            game.mkdir()
            (mods / "BetterUI" / "config" / "settings.json").write_text("better", encoding="utf-8")
            (mods / "Overhaul" / "config" / "settings.json").write_text("overhaul", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            project.set_mod_enabled("betterui", False)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)

            self.assertEqual((staging / "config" / "settings.json").read_text(encoding="utf-8"), "overhaul")
            self.assertEqual(manifest.copied_files, ["config/settings.json"])
            self.assertEqual(manifest.skipped_files, [])
            self.assertTrue(all(record.source_mod == "Overhaul" for record in manifest.records))

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
            disk_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            overwrite_record = next(record for record in manifest.records if record.status == "overwritten")
            backup_path = Path(overwrite_record.backup_path)

            self.assertEqual(manifest.target, "game")
            self.assertEqual(Path(manifest.target_root), game.resolve(strict=False))
            self.assertEqual(Path(manifest.backup_dir), staging.parent / "backups" / manifest.manifest_id)
            self.assertEqual(manifest.backups, ["config/settings.json"])
            self.assertTrue(backup_path.exists())
            self.assertEqual(backup_path.read_text(encoding="utf-8"), "original")
            self.assertEqual(disk_payload["target"], "game")
            self.assertEqual(disk_payload["manifest_id"], manifest.manifest_id)
            self.assertEqual(disk_payload["records"][0]["backup_path"], str(backup_path))
            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "patched")
            self.assertEqual((game / "textures" / "new.txt").read_text(encoding="utf-8"), "new")
            self.assertEqual(manifest.overwritten_files, ["config/settings.json"])
            self.assertEqual(manifest.copied_files, ["textures/new.txt"])
            self.assertTrue(manifest_path.exists())

            preview = preview_restore_manifest(manifest_path)
            actions = {record.destination_path: record.action for record in preview.records}
            self.assertEqual(actions["config/settings.json"], "restore-backup")
            self.assertEqual(actions["textures/new.txt"], "remove-created-file")
            self.assertFalse(preview.warnings)
            preview_payload = preview.to_dict()
            self.assertTrue(preview_payload["can_restore"])
            self.assertEqual(preview_payload["restore_from_backup"], 1)
            self.assertEqual(preview_payload["delete_copied_files"], 1)

            restored = restore_manifest(manifest_path)

            self.assertTrue(restored.restored_at)
            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "original")
            self.assertFalse((game / "textures" / "new.txt").exists())

    def test_apply_to_game_rejects_missing_game_root_before_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "missing-game"
            staging = root / ".modforge" / "staging"
            package_root = root / "mods" / "Patch"
            package_root.mkdir(parents=True)
            (package_root / "settings.txt").write_text("patched", encoding="utf-8")

            project = ModProject.create("Demo", game, root / "mods", staging)
            package = ModPackage(
                id="patch",
                name="Patch",
                path=package_root,
                enabled=True,
                priority=0,
                detected_type="loose_folder",
                files=[ModFile("settings.txt", 7)],
            )
            plan = DeploymentPlan(
                project_name="Demo",
                operations=[DeploymentOperation("Patch", "settings.txt", "settings.txt")],
            )

            with self.assertRaises(FileNotFoundError):
                apply_to_game(project, plan, [package])
            self.assertFalse((staging.parent / "manifests").exists())
            self.assertFalse((staging.parent / "backups").exists())

    def test_priority_reorder_changes_apply_winner_after_replan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            (mods / "Base" / "config").mkdir(parents=True)
            (mods / "Patch" / "config").mkdir(parents=True)
            game.mkdir()
            (mods / "Base" / "config" / "settings.json").write_text("base", encoding="utf-8")
            (mods / "Patch" / "config" / "settings.json").write_text("patch", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            first_plan = build_deployment_plan(project, packages)
            first_manifest = apply_to_staging(project, first_plan, packages)

            self.assertEqual((staging / "config" / "settings.json").read_text(encoding="utf-8"), "patch")
            self.assertEqual(first_manifest.skipped_files, ["config/settings.json"])

            project.set_priority_order(["patch", "base"])
            reordered_packages = scan_mods(project.mods_dir, project.active_profile())
            second_plan = build_deployment_plan(project, reordered_packages)
            second_manifest = apply_to_staging(project, second_plan, reordered_packages)

            self.assertEqual((staging / "config" / "settings.json").read_text(encoding="utf-8"), "base")
            self.assertEqual(second_plan.conflicts[0].winning_mod, "Base")
            self.assertEqual(second_manifest.overwritten_files, ["config/settings.json"])
            self.assertEqual(second_manifest.skipped_files, ["config/settings.json"])

    def test_restore_rejects_staging_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / "staging"
            (mods / "Patch").mkdir(parents=True)
            game.mkdir()
            (mods / "Patch" / "settings.txt").write_text("patched", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            apply_to_staging(project, plan, packages)
            manifest_path = staging / ".modforge-install-manifest.json"

            with self.assertRaisesRegex(ValueError, "Only game manifests can be restored"):
                preview_restore_manifest(manifest_path)
            with self.assertRaisesRegex(ValueError, "Only game manifests can be restored"):
                restore_manifest(manifest_path)

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

    def test_restore_preview_reports_missing_backup_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            (mods / "Patch" / "config").mkdir(parents=True)
            (game / "config").mkdir(parents=True)
            (mods / "Patch" / "config" / "settings.json").write_text("patched", encoding="utf-8")
            (game / "config" / "settings.json").write_text("original", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = staging.parent / "manifests" / f"{manifest.manifest_id}.json"
            backup_path = Path(manifest.records[0].backup_path)
            backup_path.unlink()

            preview = preview_restore_manifest(manifest_path)

            self.assertIn("Backup is missing", preview.warnings[0])
            self.assertFalse(preview.to_dict()["can_restore"])
            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "patched")

            with self.assertRaises(FileNotFoundError):
                restore_manifest(manifest_path)
            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "patched")

    def test_restore_rejects_partial_unmatched_selected_paths_before_writing(self) -> None:
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

            preview = preview_restore_manifest(manifest_path, ["config/settings.json", "missing.txt"])
            self.assertIn("No restorable record matched selected path: missing.txt", preview.warnings)

            with self.assertRaises(ValueError):
                restore_manifest(manifest_path, ["config/settings.json", "missing.txt"])

            self.assertEqual((game / "config" / "settings.json").read_text(encoding="utf-8"), "patched")

    def test_restore_preview_and_restore_block_unsafe_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            manifest_path = root / "manifest.json"
            game.mkdir()
            manifest = InstallManifest(
                manifest_id="unsafe",
                target="game",
                target_root=str(game),
                records=[
                    InstallRecord(
                        destination_path="../escape.txt",
                        source_mod="Patch",
                        source_path="../escape.txt",
                        status="copied",
                    )
                ],
            )
            manifest.save(manifest_path)

            preview = preview_restore_manifest(manifest_path)

            self.assertEqual(preview.records[0].action, "blocked")
            self.assertIn("Refusing unsafe relative path", preview.warnings[0])
            self.assertFalse(preview.to_dict()["can_restore"])
            with self.assertRaises(ValueError):
                restore_manifest(manifest_path)

    def test_restore_blocks_backups_outside_manifest_backup_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            backup_dir = root / "backups" / "manifest"
            outside_backup = root / "outside-backup.txt"
            manifest_path = root / "manifest.json"
            game.mkdir()
            backup_dir.mkdir(parents=True)
            outside_backup.write_text("original", encoding="utf-8")
            (game / "settings.txt").write_text("patched", encoding="utf-8")
            manifest = InstallManifest(
                manifest_id="outside-backup",
                target="game",
                target_root=str(game),
                backup_dir=str(backup_dir),
                records=[
                    InstallRecord(
                        destination_path="settings.txt",
                        source_mod="Patch",
                        source_path="settings.txt",
                        status="overwritten",
                        backup_path=str(outside_backup),
                    )
                ],
            )
            manifest.save(manifest_path)

            preview = preview_restore_manifest(manifest_path)

            self.assertIn("Backup is outside manifest backup directory", preview.warnings[0])
            with self.assertRaises(ValueError):
                restore_manifest(manifest_path)
            self.assertEqual((game / "settings.txt").read_text(encoding="utf-8"), "patched")

    def test_loose_folder_source_paths_must_stay_inside_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            staging = root / "staging"
            package_root = root / "mods" / "Unsafe"
            outside = root / "outside.txt"
            game.mkdir()
            package_root.mkdir(parents=True)
            outside.write_text("outside", encoding="utf-8")

            project = ModProject.create("Demo", game, root / "mods", staging)
            package = ModPackage(
                id="unsafe",
                name="Unsafe",
                path=package_root,
                enabled=True,
                priority=0,
                detected_type="loose_folder",
                files=[ModFile("../outside.txt", outside.stat().st_size)],
            )
            plan = DeploymentPlan(
                project_name="Demo",
                operations=[
                    DeploymentOperation(
                        source_mod="Unsafe",
                        source_path="../outside.txt",
                        destination_path="outside.txt",
                    )
                ],
            )

            with self.assertRaises(ValueError):
                apply_to_staging(project, plan, [package])
            self.assertFalse((staging / "outside.txt").exists())

    def test_staging_preflight_blocks_partial_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            staging = root / "staging"
            package_root = root / "mods" / "Patch"
            game.mkdir()
            package_root.mkdir(parents=True)
            (package_root / "safe.txt").write_text("safe", encoding="utf-8")

            project = ModProject.create("Demo", game, root / "mods", staging)
            package = ModPackage(
                id="patch",
                name="Patch",
                path=package_root,
                enabled=True,
                priority=0,
                detected_type="loose_folder",
                files=[
                    ModFile("safe.txt", 4),
                    ModFile("../missing.txt", 0),
                ],
            )
            plan = DeploymentPlan(
                project_name="Demo",
                operations=[
                    DeploymentOperation("Patch", "safe.txt", "safe.txt"),
                    DeploymentOperation("Patch", "../missing.txt", "missing.txt"),
                ],
            )

            with self.assertRaises(ValueError):
                apply_to_staging(project, plan, [package])
            self.assertFalse((staging / "safe.txt").exists())

    def test_game_apply_preflight_blocks_partial_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            staging = root / ".modforge" / "staging"
            package_root = root / "mods" / "Patch"
            game.mkdir()
            package_root.mkdir(parents=True)
            (package_root / "safe.txt").write_text("safe", encoding="utf-8")

            project = ModProject.create("Demo", game, root / "mods", staging)
            package = ModPackage(
                id="patch",
                name="Patch",
                path=package_root,
                enabled=True,
                priority=0,
                detected_type="loose_folder",
                files=[
                    ModFile("safe.txt", 4),
                    ModFile("../missing.txt", 0),
                ],
            )
            plan = DeploymentPlan(
                project_name="Demo",
                operations=[
                    DeploymentOperation("Patch", "safe.txt", "safe.txt"),
                    DeploymentOperation("Patch", "../missing.txt", "missing.txt"),
                ],
            )

            with self.assertRaises(ValueError):
                apply_to_game(project, plan, [package])
            self.assertFalse((game / "safe.txt").exists())
            self.assertFalse((staging.parent / "manifests").exists())
            self.assertFalse((staging.parent / "backups").exists())

    def test_selected_unreal_sidecar_restore_expands_to_atomic_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            mod_root = mods / "TextureTriplet"
            target_root = game / "Content" / "Paks" / "~mods"
            mod_root.mkdir(parents=True)
            target_root.mkdir(parents=True)
            for suffix in [".pak", ".ucas", ".utoc"]:
                (mod_root / f"TextureTriplet_P{suffix}").write_text(f"patched {suffix}", encoding="utf-8")
                (target_root / f"TextureTriplet_P{suffix}").write_text(f"original {suffix}", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging, game_profile="unreal-pak")
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = staging.parent / "manifests" / f"{manifest.manifest_id}.json"

            selected = "Content/Paks/~mods/TextureTriplet_P.pak"
            preview = preview_restore_manifest(manifest_path, [selected])

            self.assertEqual(
                sorted(preview.selected_paths),
                [
                    "Content/Paks/~mods/TextureTriplet_P.pak",
                    "Content/Paks/~mods/TextureTriplet_P.ucas",
                    "Content/Paks/~mods/TextureTriplet_P.utoc",
                ],
            )

            restore_manifest(manifest_path, [selected])

            for suffix in [".pak", ".ucas", ".utoc"]:
                self.assertEqual(
                    (target_root / f"TextureTriplet_P{suffix}").read_text(encoding="utf-8"),
                    f"original {suffix}",
                )

    def test_top_level_unreal_sidecars_copy_from_their_own_archive_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            mods.mkdir()
            game.mkdir()
            for suffix in [".pak", ".ucas", ".utoc"]:
                (mods / f"TextureTriplet_P{suffix}").write_text(f"{suffix}-bytes", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging, game_profile="unreal-pak")
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)

            apply_to_staging(project, plan, packages)

            target_root = staging / "Content" / "Paks" / "~mods"
            for suffix in [".pak", ".ucas", ".utoc"]:
                self.assertEqual(
                    (target_root / f"TextureTriplet_P{suffix}").read_text(encoding="utf-8"),
                    f"{suffix}-bytes",
                )

    def test_apply_rejects_destination_symlink_before_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            (mods / "Patch").mkdir(parents=True)
            game.mkdir()
            protected = game / "protected.txt"
            protected.write_text("original", encoding="utf-8")
            try:
                (game / "linked.txt").symlink_to(protected)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            (mods / "Patch" / "linked.txt").write_text("patched", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)

            with self.assertRaises(ValueError):
                apply_to_game(project, plan, packages)
            self.assertEqual(protected.read_text(encoding="utf-8"), "original")
            self.assertFalse((staging.parent / "manifests").exists())
            self.assertFalse((staging.parent / "backups").exists())


if __name__ == "__main__":
    unittest.main()
