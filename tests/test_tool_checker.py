from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
