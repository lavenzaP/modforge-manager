from __future__ import annotations

import unittest

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.conflict_detector import detect_conflicts


class ConflictDetectorTests(unittest.TestCase):
    def test_highest_priority_wins_conflict(self) -> None:
        conflicts = detect_conflicts(
            [
                ("config/settings.json", "BetterUI", 0),
                ("config/settings.json", "Overhaul", 1),
                ("scripts/main.lua", "Overhaul", 1),
            ]
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].winning_mod, "Overhaul")

    def test_windows_case_insensitive_destination_conflicts(self) -> None:
        conflicts = detect_conflicts(
            [
                ("Content/Paks/~mods/CoolPak_P.pak", "CoolPak", 0),
                ("content/paks/~mods/coolpak_p.PAK", "CoolPakAlt", 1),
            ]
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].destination_path, "Content/Paks/~mods/CoolPak_P.pak")
        self.assertEqual(conflicts[0].mods, ["CoolPak", "CoolPakAlt"])
        self.assertEqual(conflicts[0].winning_mod, "CoolPakAlt")


if __name__ == "__main__":
    unittest.main()
