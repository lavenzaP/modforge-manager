from __future__ import annotations

import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.game_profile import DeploymentRule, GameProfile


class GameProfileTests(unittest.TestCase):
    def test_generic_profile_has_default_rule(self) -> None:
        profile = GameProfile.generic()

        self.assertEqual(profile.id, "generic-folder")
        self.assertEqual(len(profile.deployment_rules), 1)

    def test_rule_serializes(self) -> None:
        rule = DeploymentRule(destination_root="Data")

        self.assertEqual(rule.to_dict()["destination_root"], "Data")


if __name__ == "__main__":
    unittest.main()
