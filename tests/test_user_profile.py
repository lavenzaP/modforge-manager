from __future__ import annotations

from pathlib import Path
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class UserProfileTests(unittest.TestCase):
    def test_project_can_create_switch_clone_and_delete_user_profiles(self) -> None:
        project = ModProject.create(
            name="Demo",
            game_root=FIXTURES / "fake_game",
            mods_dir=FIXTURES / "fake_mods",
            staging_dir=FIXTURES / "staging",
        )
        project.set_mod_enabled("betterui", False)
        project.set_priority_order(["overhaul", "betterui"])

        profile = project.create_user_profile("Boss Run", name="Boss Run", copy_from="default")
        self.assertEqual(profile.id, "boss-run")
        project.switch_user_profile("boss-run")
        self.assertFalse(project.active_profile().is_enabled("betterui"))
        self.assertEqual(project.active_profile().mod_priority_order, ["overhaul", "betterui"])

        project.set_mod_enabled("overhaul", False)
        project.switch_user_profile("default")
        self.assertTrue(project.active_profile().is_enabled("overhaul"))

        deleted = project.delete_user_profile("boss-run")
        self.assertEqual(deleted.id, "boss-run")
        self.assertEqual([item.id for item in project.user_profiles], ["default"])

    def test_disabled_mod_is_excluded_from_plan(self) -> None:
        project = ModProject.create(
            name="Demo",
            game_root=FIXTURES / "fake_game",
            mods_dir=FIXTURES / "fake_mods",
            staging_dir=FIXTURES / "staging",
        )
        project.set_mod_enabled("betterui", False)
        packages = scan_mods(project.mods_dir, project.active_profile())
        plan = build_deployment_plan(project, packages)

        self.assertEqual([package.enabled for package in packages], [False, True])
        self.assertEqual(len(plan.conflicts), 0)
        self.assertTrue(all(operation.source_mod == "Overhaul" for operation in plan.operations))


if __name__ == "__main__":
    unittest.main()
