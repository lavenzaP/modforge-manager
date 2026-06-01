from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_staging
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
from modforge.core.mod_project import ModProject


class DeployerTests(unittest.TestCase):
    def test_apply_to_staging_copies_winners_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / "staging"
            (mods / "A" / "config").mkdir(parents=True)
            (mods / "B" / "config").mkdir(parents=True)
            game.mkdir()
            (mods / "A" / "config" / "settings.json").write_text("a", encoding="utf-8")
            (mods / "B" / "config" / "settings.json").write_text("b", encoding="utf-8")

            project = ModProject.create("Demo", game, mods, staging)
            packages = scan_mods(project.mods_dir, project.active_profile())
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)

            self.assertEqual((staging / "config" / "settings.json").read_text(encoding="utf-8"), "b")
            self.assertEqual(manifest.skipped_files, ["config/settings.json"])
            self.assertTrue((staging / ".modforge-install-manifest.json").exists())
            self.assertFalse((game / "config" / "settings.json").exists())


if __name__ == "__main__":
    unittest.main()
