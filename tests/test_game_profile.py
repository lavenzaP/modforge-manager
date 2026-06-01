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
        self.assertEqual(builtin_profile("unreal-pak").display_name, "Unreal PAK ~mods Workflow")


if __name__ == "__main__":
    unittest.main()
