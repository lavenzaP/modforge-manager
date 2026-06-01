from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.cli import main


class CliTests(unittest.TestCase):
    def test_cli_project_scan_plan_tools_and_translation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            output_csv = root / "strings.csv"
            (mods / "ModOne").mkdir(parents=True)
            game.mkdir()
            (mods / "ModOne" / "strings.json").write_text('{"hello": "Hello"}', encoding="utf-8")

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "project",
                            "init",
                            "--name",
                            "Demo",
                            "--game-root",
                            str(game),
                            "--mods-dir",
                            str(mods),
                            "--project-file",
                            str(project_file),
                        ]
                    ),
                    0,
                )
                self.assertEqual(main(["scan-mods", "--project-file", str(project_file), "--json"]), 0)
                self.assertEqual(main(["plan", "--project-file", str(project_file), "--json"]), 0)
                self.assertEqual(main(["tools", "check", "--project-file", str(project_file)]), 0)
                self.assertEqual(
                    main(["translation", "extract", "--source", str(mods), "--output", str(output_csv)]),
                    0,
                )
                self.assertEqual(
                    main(["apply-game", "--project-file", str(project_file), "--yes", "--json"]),
                    0,
                )
                manifests = sorted((root / ".modforge" / "manifests").glob("*.json"))
                self.assertEqual(
                    main(["restore", "--manifest", str(manifests[0]), "--yes", "--json"]),
                    0,
                )

            self.assertTrue(output_csv.exists())
            self.assertEqual(json.loads(project_file.read_text(encoding="utf-8"))["name"], "Demo")


if __name__ == "__main__":
    unittest.main()
