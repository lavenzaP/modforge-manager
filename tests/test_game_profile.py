from __future__ import annotations

import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.game_profile import DeploymentRule, GameProfile, builtin_profile, builtin_profiles


class GameProfileTests(unittest.TestCase):
    def test_generic_profile_has_default_rule(self) -> None:
        profile = GameProfile.generic()

        self.assertEqual(profile.id, "generic-folder")
        self.assertEqual(len(profile.deployment_rules), 1)

    def test_rule_serializes(self) -> None:
        rule = DeploymentRule(destination_root="Data")

        self.assertEqual(rule.to_dict()["destination_root"], "Data")

    def test_builtin_profiles_are_addressable(self) -> None:
        ids = [profile.id for profile in builtin_profiles()]

        self.assertIn("generic-folder", ids)
        self.assertIn("unity-bepinex", ids)
        self.assertIn("unity-melonloader", ids)
        self.assertIn("bethesda-data", ids)
        self.assertIn("cyberpunk-2077", ids)
        self.assertIn("mhw-reframework", ids)
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


if __name__ == "__main__":
    unittest.main()
