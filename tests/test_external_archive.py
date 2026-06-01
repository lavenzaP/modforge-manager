from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.deployer import apply_to_staging
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_project_mods
from modforge.core.mod_project import ModProject


class ExternalArchiveTests(unittest.TestCase):
    def test_configured_pck_tool_extracts_for_scan_plan_and_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            mods.mkdir()
            game.mkdir()
            archive = mods / "StoryPack.pck"
            archive.write_bytes(b"fake pck")

            project = ModProject.create("Demo", game, mods, staging, game_profile="godot-pck")
            project.set_tool_path("godot_pck_tool", _fake_extractor_command(root))
            packages = scan_project_mods(project)
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)

            self.assertEqual(packages[0].detected_type, "godot_pck")
            self.assertEqual([file.relative_path for file in packages[0].files], ["assets/dialogue.json"])
            self.assertFalse(any("deferred" in warning for warning in packages[0].warnings))
            self.assertEqual([operation.destination_path for operation in plan.operations], ["assets/dialogue.json"])
            self.assertEqual(manifest.copied_files, ["assets/dialogue.json"])
            self.assertEqual((staging / "assets" / "dialogue.json").read_text(encoding="utf-8"), '{"hello": "world"}')

    def test_configured_unrealpak_tool_extracts_for_scan_and_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mods = root / "mods"
            game = root / "game"
            staging = root / ".modforge" / "staging"
            mods.mkdir()
            game.mkdir()
            archive = mods / "Patch.pak"
            archive.write_bytes(b"fake pak")

            project = ModProject.create("Demo", game, mods, staging, game_profile="unreal-pak")
            project.set_tool_path("unreal_pak", _fake_extractor_command(root))
            packages = scan_project_mods(project)
            plan = build_deployment_plan(project, packages)

            self.assertEqual(packages[0].detected_type, "unreal_pak")
            self.assertEqual([file.relative_path for file in packages[0].files], ["Content/Characters/Hero.uasset"])
            self.assertEqual([operation.destination_path for operation in plan.operations], ["Content/Characters/Hero.uasset"])


def _fake_extractor_command(root: Path) -> str:
    script = root / "fake_extractor.py"
    script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "archive = Path(sys.argv[1])",
                "output = Path(sys.argv[2])",
                "if archive.suffix.lower() == '.pck':",
                "    target = output / 'assets' / 'dialogue.json'",
                "    target.parent.mkdir(parents=True, exist_ok=True)",
                "    target.write_text('{\"hello\": \"world\"}', encoding='utf-8')",
                "else:",
                "    target = output / 'Content' / 'Characters' / 'Hero.uasset'",
                "    target.parent.mkdir(parents=True, exist_ok=True)",
                "    target.write_text('asset', encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )
    return f'"{sys.executable}" "{script}" "{{archive}}" "{{output}}"'


if __name__ == "__main__":
    unittest.main()
