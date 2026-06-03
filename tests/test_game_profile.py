from __future__ import annotations

import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.game_profile import (
    DeploymentRule,
    GameProfile,
    preview_profile_paths,
    validate_profile,
    builtin_profile,
    builtin_profiles,
)


class GameProfileTests(unittest.TestCase):
    def test_generic_profile_has_default_rule(self) -> None:
        profile = GameProfile.generic()

        self.assertEqual(profile.id, "generic-folder")
        self.assertEqual(len(profile.deployment_rules), 1)

    def test_rule_serializes(self) -> None:
        rule = DeploymentRule(destination_root="Data")

        self.assertEqual(rule.to_dict()["destination_root"], "Data")

    def test_rule_can_preserve_package_name(self) -> None:
        rule = DeploymentRule(
            destination_root="mods",
            destination_pattern="{package_name}/{relative_path}",
        )

        self.assertEqual(
            rule.destination_for_relative(
                "mod_manifest.json",
                package_id="silentskin",
                package_name="silentSkin",
            ),
            "mods/silentSkin/mod_manifest.json",
        )

    def test_builtin_profiles_are_addressable(self) -> None:
        ids = [profile.id for profile in builtin_profiles()]

        self.assertIn("generic-folder", ids)
        self.assertIn("unity-bepinex", ids)
        self.assertIn("unity-melonloader", ids)
        self.assertIn("bethesda-data", ids)
        self.assertIn("cyberpunk-2077", ids)
        self.assertIn("mhw-reframework", ids)
        self.assertIn("stellar-blade.experimental", ids)
        self.assertEqual(builtin_profile("unreal-pak").display_name, "Unreal PAK ~mods Workflow")
        self.assertEqual(
            builtin_profile("mhw-reframework").display_name,
            "Monster Hunter Wilds / REFramework NativePC Workflow",
        )

    def test_mhw_reframework_profile_maps_safe_roots(self) -> None:
        profile = builtin_profile("mhw-reframework")
        destinations = [
            rule.destination_for_relative("reframework/data/BoneSystem/settings.json")
            for rule in profile.deployment_rules
            if rule.matches("reframework/data/BoneSystem/settings.json")
        ]

        self.assertEqual(destinations, ["reframework/data/BoneSystem/settings.json"])
        self.assertFalse(any(rule.matches("random/file.txt") for rule in profile.deployment_rules))

    def test_stellar_blade_profile_validates_and_maps_multi_root_rules(self) -> None:
        profile = builtin_profile("stellar-blade.experimental")
        report = validate_profile(profile)
        self.assertFalse(report.has_errors)

        mappings = {
            mapping.source_path: mapping
            for mapping in preview_profile_paths(
                profile,
                [
                    "CoolOutfit_P.pak",
                    "CoolOutfit_P.ucas",
                    "CoolOutfit_P.utoc",
                    "CoolOutfit_P.json",
                    "dwmapi.dll",
                    "UE4SS.dll",
                    "SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua",
                    "SB/Binaries/Win64/version.dll",
                    "SB/Content/Paks/~mods/AlreadyPacked_P.pak",
                ],
            )
        }

        self.assertEqual(mappings["CoolOutfit_P.pak"].destination_path, "SB/Content/Paks/~mods/CoolOutfit_P.pak")
        self.assertEqual(mappings["CoolOutfit_P.json"].destination_path, "SB/Content/Paks/~mods/CoolOutfit_P.json")
        self.assertEqual(mappings["dwmapi.dll"].destination_path, "SB/Binaries/Win64/dwmapi.dll")
        self.assertEqual(mappings["UE4SS.dll"].destination_path, "SB/Binaries/Win64/UE4SS.dll")
        self.assertIn("High-risk destination", mappings["dwmapi.dll"].warnings[0])
        self.assertEqual(
            mappings["SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua"].destination_path,
            "SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua",
        )
        self.assertEqual(
            mappings["SB/Binaries/Win64/version.dll"].destination_path,
            "SB/Binaries/Win64/version.dll",
        )
        self.assertTrue(mappings["SB/Binaries/Win64/version.dll"].warnings)
        self.assertEqual(
            mappings["SB/Content/Paks/~mods/AlreadyPacked_P.pak"].destination_path,
            "SB/Content/Paks/~mods/AlreadyPacked_P.pak",
        )
        self.assertEqual(mappings["CoolOutfit_P.pak"].group_id, "unreal-sidecar:cooloutfit_p")

    def test_custom_profile_validation_rejects_unsafe_destination(self) -> None:
        profile = GameProfile.from_dict(
            {
                "id": "bad-profile",
                "display_name": "Bad Profile",
                "root_aliases": {"game_root": "."},
                "deployment_rules": [
                    {
                        "id": "escape",
                        "source_pattern": "*.pak",
                        "destination_root": "game_root",
                        "destination_pattern": "../outside/{filename}",
                    }
                ],
            }
        )

        report = validate_profile(profile)

        self.assertTrue(report.has_errors)
        self.assertTrue(any("Unsafe destination_pattern" in issue.message for issue in report.issues))

    def test_profile_path_can_be_loaded_by_builtin_profile_resolver(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = f"{temp}/custom-profile.json"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    """{
  "schema_version": 1,
  "id": "custom-sample",
  "display_name": "Custom Sample",
  "deployment_rules": [{"id": "mods", "source_pattern": "*.pak", "destination_root": "Mods"}]
}"""
                )

            profile = builtin_profile(path)

            self.assertEqual(profile.id, "custom-sample")


if __name__ == "__main__":
    unittest.main()
