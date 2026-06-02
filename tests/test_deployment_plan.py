from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployment_plan import build_deployment_plan, summarize_deployment_plan
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
        self.assertEqual(plan.conflicts[0].winning_mod, "Overhaul")

        project.set_priority_order(["overhaul", "betterui"])
        reordered = build_deployment_plan(project, scan_mods(project.mods_dir, project.active_profile()))

        self.assertEqual(len(reordered.conflicts), 1)
        self.assertEqual(reordered.conflicts[0].destination_path, "config/settings.json")
        self.assertEqual(reordered.conflicts[0].winning_mod, "BetterUI")

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

        self.assertIn("mods/BetterUI/config/settings.json", [operation.destination_path for operation in plan.operations])

    def test_sts2_loose_mod_manifests_preserve_mod_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "silentSkin").mkdir(parents=True)
            (mods / "STS2-RitsuLib").mkdir(parents=True)
            game.mkdir()
            (mods / "silentSkin" / "mod_manifest.json").write_text('{"id": "silentSkin"}', encoding="utf-8")
            (mods / "silentSkin" / "silentSkin.pck").write_bytes(b"pck")
            (mods / "STS2-RitsuLib" / "mod_manifest.json").write_text('{"id": "STS2-RitsuLib"}', encoding="utf-8")
            project = ModProject.create("STS2", game, mods, root / "staging", game_profile="sts2-mods")

            plan = build_deployment_plan(project, scan_mods(project.mods_dir))
            destinations = sorted(operation.destination_path for operation in plan.operations)

            self.assertEqual(
                destinations,
                [
                    "mods/STS2-RitsuLib/mod_manifest.json",
                    "mods/silentSkin/mod_manifest.json",
                    "mods/silentSkin/silentSkin.pck",
                ],
            )
            self.assertEqual(plan.conflicts, [])

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

    def test_stellar_blade_profile_maps_cns_and_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "CNSOutfit").mkdir(parents=True)
            (mods / "Runtime").mkdir(parents=True)
            (mods / "AlreadyLayout" / "SB" / "Content" / "Paks" / "~mods").mkdir(parents=True)
            game.mkdir()
            for suffix in [".pak", ".ucas", ".utoc"]:
                (mods / "CNSOutfit" / f"CoolOutfit_P{suffix}").write_bytes(b"archive")
            (mods / "CNSOutfit" / "CoolOutfit_P.json").write_text("{}", encoding="utf-8")
            (mods / "Runtime" / "dwmapi.dll").write_bytes(b"dll")
            (mods / "AlreadyLayout" / "SB" / "Content" / "Paks" / "~mods" / "Already_P.pak").write_bytes(b"archive")
            project = ModProject.create("Stellar", game, mods, root / "staging", game_profile="stellar-blade.experimental")

            plan = build_deployment_plan(project, scan_mods(project.mods_dir))
            destinations = sorted(operation.destination_path for operation in plan.operations)

            self.assertEqual(
                destinations,
                [
                    "SB/Binaries/Win64/dwmapi.dll",
                    "SB/Content/Paks/~mods/Already_P.pak",
                    "SB/Content/Paks/~mods/CoolOutfit_P.json",
                    "SB/Content/Paks/~mods/CoolOutfit_P.pak",
                    "SB/Content/Paks/~mods/CoolOutfit_P.ucas",
                    "SB/Content/Paks/~mods/CoolOutfit_P.utoc",
                ],
            )
            self.assertTrue(any("high-risk destination" in warning for warning in plan.warnings))
            self.assertTrue(any("matches a protected path" in warning for warning in plan.warnings))

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

    def test_mhw_reframework_profile_reports_conflict_warning_and_summary(self) -> None:
        project = ModProject.create(
            name="MHW Demo",
            game_root=FIXTURES / "mhw_reframework_game",
            mods_dir=FIXTURES / "mhw_reframework_mods",
            staging_dir=FIXTURES / "staging",
            game_profile="mhw-reframework",
        )

        plan = build_deployment_plan(project, scan_mods(project.mods_dir))
        summary = summarize_deployment_plan(plan)

        self.assertEqual(len(plan.operations), 6)
        self.assertEqual(len(plan.conflicts), 1)
        self.assertEqual(
            plan.conflicts[0].to_dict(),
            {
                "destination_path": "nativePC/wp/swo/swo001/mod/swo001.mod3",
                "mods": ["NativeSword", "NativeSwordPatch"],
                "winning_mod": "NativeSwordPatch",
            },
        )
        self.assertEqual(
            plan.warnings,
            ["LooseNotes: no deployment rule for docs/install.txt"],
        )
        self.assertEqual(
            summary,
            {
                "project_name": "MHW Demo",
                "dry_run": True,
                "operations": 6,
                "winning_operations": 5,
                "skipped_by_conflict": 1,
                "conflicts": 1,
                "warnings": 1,
                "risk_level": "high",
            },
        )

    def test_case_insensitive_conflict_affects_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            (mods / "A").mkdir(parents=True)
            (mods / "B").mkdir(parents=True)
            game.mkdir()
            (mods / "A" / "Config").mkdir()
            (mods / "B" / "config").mkdir()
            (mods / "A" / "Config" / "Settings.json").write_text("a", encoding="utf-8")
            (mods / "B" / "config" / "settings.JSON").write_text("b", encoding="utf-8")
            project = ModProject.create("Demo", game, mods, root / "staging")

            plan = build_deployment_plan(project, scan_mods(project.mods_dir))
            summary = summarize_deployment_plan(plan)

            self.assertEqual(len(plan.conflicts), 1)
            self.assertEqual(plan.conflicts[0].winning_mod, "B")
            self.assertEqual(summary["skipped_by_conflict"], 1)

    def test_same_mod_duplicate_destination_casing_warns_and_keeps_one_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            mods.mkdir()
            game.mkdir()
            with ZipFile(mods / "CasePack.zip", "w") as archive:
                archive.writestr("Config/Settings.json", "a")
                archive.writestr("config/settings.JSON", "b")
            project = ModProject.create("Demo", game, mods, root / "staging")

            plan = build_deployment_plan(project, scan_mods(project.mods_dir))

            self.assertEqual(len(plan.operations), 1)
            self.assertEqual(plan.operations[0].source_path, "Config/Settings.json")
            self.assertEqual(len(plan.conflicts), 0)
            self.assertIn("duplicate destination variants", plan.warnings[0])


if __name__ == "__main__":
    unittest.main()
