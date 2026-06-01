from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class DeploymentPlanTests(unittest.TestCase):
    def test_plan_detects_fake_mod_conflict(self) -> None:
        project = ModProject.create(
            name="Demo",
            game_root=FIXTURES / "fake_game",
            mods_dir=FIXTURES / "fake_mods",
            staging_dir=FIXTURES / "staging",
        )
        plan = build_deployment_plan(project, scan_mods(project.mods_dir))

        self.assertEqual(len(plan.operations), 4)
        self.assertEqual(len(plan.conflicts), 1)
        self.assertEqual(plan.conflicts[0].destination_path, "config/settings.json")

    def test_profile_rules_map_destinations_and_ignored_files(self) -> None:
        project = ModProject.create(
            name="Demo",
            game_root=FIXTURES / "fake_game",
            mods_dir=FIXTURES / "fake_mods",
            staging_dir=FIXTURES / "staging",
            game_profile="sts2-mods",
        )
        packages = scan_mods(project.mods_dir)
        plan = build_deployment_plan(project, packages)

        self.assertIn("mods/config/settings.json", [operation.destination_path for operation in plan.operations])

    def test_mo2_profile_ignores_meta_ini(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "Example").mkdir(parents=True)
            game.mkdir()
            (mods / "Example" / "meta.ini").write_text("[General]", encoding="utf-8")
            (mods / "Example" / "DataFile.txt").write_text("payload", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="mo2-mod")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual([operation.destination_path for operation in plan.operations], ["DataFile.txt"])

    def test_unreal_profile_maps_paks_to_mods_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "PakMod").mkdir(parents=True)
            game.mkdir()
            (mods / "PakMod" / "Example.pak").write_bytes(b"fake")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="unreal-pak")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(
                plan.operations[0].destination_path,
                "Content/Paks/~mods/Example.pak",
            )


if __name__ == "__main__":
    unittest.main()
