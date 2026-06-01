from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_game, apply_to_staging, preview_restore_manifest, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan, summarize_deployment_plan
from modforge.core.mod_package import scan_project_mods
from modforge.core.mod_project import ModProject
from modforge.translation.exporter import extract_strings


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mod_families"


class ModFamilyCertificationTests(unittest.TestCase):
    def test_reframework_wilds_family_certification(self) -> None:
        with _family_project("reframework_wilds", "mhw-reframework") as project:
            packages = scan_project_mods(project)
            plan = build_deployment_plan(project, packages)
            summary = summarize_deployment_plan(plan)

            self.assertEqual([package.name for package in packages], [
                "AutorunHelper",
                "BoneSystemBase",
                "BoneSystemPatch",
                "NativeWeapon",
            ])
            self.assertEqual(len(plan.conflicts), 1)
            self.assertEqual(plan.conflicts[0].destination_path, "reframework/data/BoneSystem/monster_a.json")
            self.assertEqual(plan.conflicts[0].winning_mod, "BoneSystemPatch")
            self.assertEqual(summary["risk_level"], "high")
            self.assertTrue(all(
                operation.destination_path.startswith(("reframework/", "nativePC/"))
                for operation in plan.operations
            ))

            apply_to_staging(project, plan, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = project.staging_dir.parent / "manifests" / f"{manifest.manifest_id}.json"
            preview = preview_restore_manifest(manifest_path)
            self.assertTrue(preview.to_dict()["can_restore"])
            restore_manifest(manifest_path)

            self.assertFalse((project.game_root / "reframework" / "data" / "BoneSystem" / "monster_a.json").exists())

    def test_unreal_family_certification(self) -> None:
        with _family_project("unreal_pak", "unreal-pak") as project:
            packages = scan_project_mods(project)
            plan = build_deployment_plan(project, packages)
            destinations = sorted(operation.destination_path for operation in plan.operations)
            warnings = [warning for package in packages for warning in package.warnings] + plan.warnings

            self.assertIn("Unreal sidecar set is incomplete for BrokenTriplet_P: missing .utoc", warnings)
            self.assertIn("Content/Paks/~mods/CoolPak_P.pak", destinations)
            self.assertIn("Content/Paks/~mods/TextureTriplet_P.ucas", destinations)
            self.assertIn("Content/Paks/~mods/TextureTriplet_P.utoc", destinations)
            self.assertEqual(len(plan.conflicts), 1)
            self.assertEqual(plan.conflicts[0].destination_path, "Content/Paks/~mods/CoolPak_P.pak")

            apply_to_staging(project, plan, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = project.staging_dir.parent / "manifests" / f"{manifest.manifest_id}.json"
            self.assertTrue((project.game_root / "Content" / "Paks" / "~mods" / "TextureTriplet_P.pak").exists())
            self.assertTrue(preview_restore_manifest(manifest_path).to_dict()["can_restore"])
            restore_manifest(manifest_path)
            self.assertFalse((project.game_root / "Content" / "Paks" / "~mods" / "TextureTriplet_P.pak").exists())

    def test_godot_sts2_family_certification(self) -> None:
        with _family_project("godot_sts2", "sts2-mods") as project:
            packages = scan_project_mods(project)
            plan = build_deployment_plan(project, packages)
            destinations = sorted(operation.destination_path for operation in plan.operations)
            warnings = [warning for package in packages for warning in package.warnings]

            self.assertTrue(any("No external tool configured for godot_pck" in warning for warning in warnings))
            self.assertIn("mods/balance_patch.pck", destinations)
            self.assertIn("mods/better_cards.pck", destinations)
            self.assertIn("mods/data/cards.json", destinations)
            self.assertIn("mods/localization/en.csv", destinations)
            self.assertEqual(len(plan.conflicts), 1)
            self.assertEqual(plan.conflicts[0].destination_path, "mods/better_cards.pck")

            entries = extract_strings(project.mods_dir / "LooseGodotMod")
            self.assertTrue(any(entry.source == "Strike+" for entry in entries))
            apply_to_staging(project, plan, packages)
            manifest = apply_to_game(project, plan, packages)
            manifest_path = project.staging_dir.parent / "manifests" / f"{manifest.manifest_id}.json"
            self.assertTrue((project.game_root / "mods" / "better_cards.pck").exists())
            self.assertTrue(preview_restore_manifest(manifest_path).to_dict()["can_restore"])
            restore_manifest(manifest_path)
            self.assertFalse((project.game_root / "mods" / "better_cards.pck").exists())


class _family_project:
    def __init__(self, family: str, profile: str) -> None:
        self.family = family
        self.profile = profile
        self.temp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> ModProject:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        game = root / "game"
        mods = root / "mods"
        shutil.copytree(FIXTURES / self.family / "fake_game", game)
        shutil.copytree(FIXTURES / self.family / "mods", mods)
        return ModProject.create("Demo", game, mods, root / ".modforge" / "staging", game_profile=self.profile)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.temp is not None:
            self.temp.cleanup()


if __name__ == "__main__":
    unittest.main()
