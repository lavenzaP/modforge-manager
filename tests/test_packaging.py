from __future__ import annotations

import os
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_console_scripts_are_declared(self) -> None:
        payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = payload["project"]["scripts"]

        self.assertEqual(scripts["modforge"], "modforge.cli:main")
        self.assertEqual(scripts["modforge-gui"], "modforge.app:main")
        self.assertEqual(scripts["modforge-gui-qt"], "modforge.gui.main_window:main")

    def test_python_module_entrypoint_reports_version(self) -> None:
        env = os.environ.copy()
        src_path = str(ROOT / "src")
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            src_path + os.pathsep + existing_pythonpath if existing_pythonpath else src_path
        )

        completed = subprocess.run(
            [sys.executable, "-m", "modforge", "--version"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("modforge 0.1.0", completed.stdout)

    def test_windows_smoke_scripts_exist(self) -> None:
        for name in [
            "dev_setup.ps1",
            "lint.ps1",
            "run_tests.ps1",
            "smoke_cli.ps1",
            "smoke_gui_import.ps1",
            "release_smoke.ps1",
        ]:
            self.assertTrue((ROOT / "scripts" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
