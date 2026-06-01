from __future__ import annotations

import sys
import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.tools.checker import check_tools


class ToolCheckerTests(unittest.TestCase):
    def test_missing_tools_are_warnings_not_errors(self) -> None:
        checks = check_tools({})

        self.assertGreaterEqual(len(checks), 1)
        self.assertFalse(any(check.exists for check in checks))
        self.assertTrue(all(check.warning for check in checks))

    def test_command_templates_check_the_executable_path(self) -> None:
        checks = check_tools({"godot_pck_tool": f'"{sys.executable}" "{{archive}}" "{{output}}"'})
        godot_check = next(check for check in checks if check.tool_id == "godot_pck_tool")

        self.assertTrue(godot_check.exists)
        self.assertFalse(godot_check.warning)


if __name__ == "__main__":
    unittest.main()
