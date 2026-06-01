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

    def test_bepinex_profile_maps_common_plugin_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "PluginPack" / "plugins").mkdir(parents=True)
            (mods / "PluginPack" / "config").mkdir(parents=True)
            game.mkdir()
            (mods / "PluginPack" / "Plugin.dll").write_bytes(b"dll")
            (mods / "PluginPack" / "plugins" / "Nested.dll").write_bytes(b"dll")
            (mods / "PluginPack" / "config" / "plugin.cfg").write_text("cfg", encoding="utf-8")
            (mods / "PluginPack" / "manifest.json").write_text("{}", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="unity-bepinex")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(
                sorted(operation.destination_path for operation in plan.operations),
                [
                    "BepInEx/config/plugin.cfg",
                    "BepInEx/plugins/Nested.dll",
                    "BepInEx/plugins/Plugin.dll",
                ],
            )

    def test_bethesda_profile_maps_data_folder_and_root_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "QuestPack" / "meshes").mkdir(parents=True)
            (mods / "QuestPack" / "Data" / "scripts").mkdir(parents=True)
            (mods / "QuestPack" / "fomod").mkdir(parents=True)
            game.mkdir()
            (mods / "QuestPack" / "Quest.esp").write_bytes(b"plugin")
            (mods / "QuestPack" / "meshes" / "armor.nif").write_bytes(b"mesh")
            (mods / "QuestPack" / "Data" / "scripts" / "quest.pex").write_bytes(b"script")
            (mods / "QuestPack" / "fomod" / "info.xml").write_text("<fomod />", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="bethesda-data")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(
                sorted(operation.destination_path for operation in plan.operations),
                [
                    "Data/Quest.esp",
                    "Data/meshes/armor.nif",
                    "Data/scripts/quest.pex",
                ],
            )

    def test_melonloader_profile_maps_root_dlls_to_mods(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "MelonPack" / "UserLibs").mkdir(parents=True)
            game.mkdir()
            (mods / "MelonPack" / "CoolMod.dll").write_bytes(b"dll")
            (mods / "MelonPack" / "UserLibs" / "Helper.dll").write_bytes(b"dll")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="unity-melonloader")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(
                sorted(operation.destination_path for operation in plan.operations),
                [
                    "Mods/CoolMod.dll",
                    "UserLibs/Helper.dll",
                ],
            )

    def test_cyberpunk_profile_maps_archives_and_existing_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "NightCityPatch" / "r6" / "scripts").mkdir(parents=True)
            game.mkdir()
            (mods / "NightCityPatch" / "appearance.archive").write_bytes(b"archive")
            (mods / "NightCityPatch" / "r6" / "scripts" / "patch.reds").write_text("script", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / "staging", game_profile="cyberpunk-2077")
            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(
                sorted(operation.destination_path for operation in plan.operations),
                [
                    "archive/pc/mod/appearance.archive",
                    "r6/scripts/patch.reds",
                ],
            )


if __name__ == "__main__":
    unittest.main()
