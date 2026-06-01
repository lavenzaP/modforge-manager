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
