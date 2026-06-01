from __future__ import annotations

from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
