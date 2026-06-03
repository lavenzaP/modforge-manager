from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class CliTests(unittest.TestCase):
    def run_cli(self, args: list[str]) -> tuple[int, str]:
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(args)
        return code, stdout.getvalue()

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
                            "--profile",
                            "mo2-mod",
                            "--project-file",
                            str(project_file),
                        ]
                    ),
                    0,
                )
                self.assertEqual(main(["scan-mods", "--project-file", str(project_file), "--json"]), 0)
                self.assertEqual(main(["plan", "--project-file", str(project_file), "--json"]), 0)
                self.assertEqual(main(["profiles", "--json"]), 0)
                self.assertEqual(main(["profile", "list", "--project-file", str(project_file), "--json"]), 0)
                self.assertEqual(
                    main(
                        [
                            "profile",
                            "create",
                            "Boss Run",
                            "--name",
                            "Boss Run",
                            "--copy-from",
                            "default",
                            "--project-file",
                            str(project_file),
                        ]
                    ),
                    0,
                )
                self.assertEqual(main(["profile", "switch", "boss-run", "--project-file", str(project_file)]), 0)
                self.assertEqual(main(["profile", "disable", "modone", "--project-file", str(project_file)]), 0)
                self.assertEqual(main(["profile", "switch", "default", "--project-file", str(project_file)]), 0)
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
                    main(["restore", "--manifest", str(manifests[0]), "--path", "strings.json", "--yes", "--json"]),
                    0,
                )

            self.assertTrue(output_csv.exists())
            code, output = self.run_cli(["project", "show", "--project-file", str(project_file), "--json"])
            self.assertEqual(code, 0)
            project_show = json.loads(output)
            self.assertEqual(project_show["name"], "Demo")
            self.assertEqual(project_show["game_profile"]["id"], "mo2-mod")
            payload = json.loads(project_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "Demo")
            self.assertEqual(payload["game_profile"]["id"], "mo2-mod")
            self.assertEqual(payload["active_user_profile"], "default")
            boss_profile = next(item for item in payload["user_profiles"] if item["id"] == "boss-run")
            self.assertEqual(boss_profile["disabled_mod_ids"], ["modone"])

    def test_cli_translation_inventory_reads_staging_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            mod = mods / "TextPak"
            (mod / "Content" / "Localization" / "Game" / "en").mkdir(parents=True)
            (mod / "Content" / "Data").mkdir(parents=True)
            game.mkdir()
            (mod / "CoolOutfit_P.pak").write_bytes(b"pak")
            (mod / "Content" / "Localization" / "Game" / "en" / "Game.locres").write_bytes(b"locres")
            (mod / "Content" / "Data" / "menu.json").write_text('{"start": "Start"}', encoding="utf-8")

            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "init",
                        "--name",
                        "Unreal Demo",
                        "--game-root",
                        str(game),
                        "--mods-dir",
                        str(mods),
                        "--profile",
                        "unreal-pak",
                        "--project-file",
                        str(project_file),
                    ]
                )[0],
                0,
            )
            self.assertEqual(self.run_cli(["apply-staging", "--project-file", str(project_file), "--yes"])[0], 0)

            code, output = self.run_cli([
                "translation",
                "inventory",
                "--project-file",
                str(project_file),
                "--json",
            ])
            self.assertEqual(code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["profile_id"], "unreal-pak")
            self.assertEqual(payload["target"], "staging")
            self.assertEqual(payload["summary"]["extractable"], 1)
            self.assertEqual(payload["summary"]["tool_required"], 1)
            self.assertEqual(payload["summary"]["archive_not_inspected"], 1)
            self.assertTrue(any(
                candidate["source_mod"] == "TextPak"
                for candidate in payload["candidates"]
            ))

    def test_cli_project_set_paths_preserves_profile_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            changed_mods = root / "managed" / "Mods"
            project_file = root / "modforge.project.json"
            game.mkdir()
            mods.mkdir()
            changed_mods.mkdir(parents=True)

            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "init",
                        "--name",
                        "Managed",
                        "--game-root",
                        str(game),
                        "--mods-dir",
                        str(mods),
                        "--profile",
                        "sts2-mods",
                        "--project-file",
                        str(project_file),
                    ]
                )[0],
                0,
            )
            self.assertEqual(self.run_cli(["profile", "disable", "example", "--project-file", str(project_file)])[0], 0)

            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "set-paths",
                        "--project-file",
                        str(project_file),
                        "--mods-dir",
                        str(changed_mods),
                    ]
                )[0],
                0,
            )

            payload = json.loads(project_file.read_text(encoding="utf-8"))
            self.assertEqual(Path(payload["mods_dir"]), changed_mods.resolve())
            self.assertEqual(payload["game_profile"]["id"], "sts2-mods")
            self.assertEqual(payload["user_profiles"][0]["disabled_mod_ids"], ["example"])

    def test_cli_guided_safe_workflow_preview_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            report = root / "conflict-report.md"
            conflict_path = "nativePC/wp/swo/swo001/mod/swo001.mod3"
            conflict_file = game / "nativePC" / "wp" / "swo" / "swo001" / "mod" / "swo001.mod3"
            shutil.copytree(FIXTURES / "mhw_reframework_game", game)
            shutil.copytree(FIXTURES / "mhw_reframework_mods", mods)
            conflict_file.parent.mkdir(parents=True, exist_ok=True)
            conflict_file.write_text("original sword model", encoding="utf-8")

            code, output = self.run_cli(["doctor", "--project-file", str(project_file)])
            self.assertEqual(code, 0)
            self.assertIn("Project file does not exist", output)

            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "init",
                        "--name",
                        "MHW Demo",
                        "--game-root",
                        str(game),
                        "--mods-dir",
                        str(mods),
                        "--profile",
                        "mhw-reframework",
                        "--project-file",
                        str(project_file),
                    ]
                )[0],
                0,
            )
            self.assertEqual(self.run_cli(["doctor", "--project-file", str(project_file)])[0], 0)

            code, output = self.run_cli(["scan-mods", "--project-file", str(project_file), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual([item["name"] for item in json.loads(output)], [
                "BaseScript",
                "LooseNotes",
                "NativeSword",
                "NativeSwordPatch",
            ])

            code, output = self.run_cli(
                ["plan", "--project-file", str(project_file), "--summary", "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(output),
                {
                    "project_name": "MHW Demo",
                    "dry_run": True,
                    "operations": 6,
                    "winning_operations": 5,
                    "skipped_by_conflict": 1,
                    "conflicts": 1,
                    "warnings": 1,
                    "risk_level": "high",
                },
            )
            code, output = self.run_cli(["plan", "--project-file", str(project_file), "--summary"])
            self.assertEqual(code, 0)
            self.assertIn("Risk: high", output)

            self.assertEqual(
                self.run_cli(["report", "--project-file", str(project_file), "--output", str(report)])[0],
                0,
            )
            self.assertIn("nativePC/wp/swo/swo001/mod/swo001.mod3", report.read_text(encoding="utf-8"))

            self.assertEqual(self.run_cli(["apply-staging", "--project-file", str(project_file)])[0], 2)
            self.assertFalse((root / ".modforge" / "staging" / ".modforge-install-manifest.json").exists())
            self.assertEqual(
                self.run_cli(["apply-staging", "--project-file", str(project_file), "--yes"])[0],
                0,
            )
            self.assertEqual(conflict_file.read_text(encoding="utf-8"), "original sword model")

            self.assertEqual(self.run_cli(["apply-game", "--project-file", str(project_file)])[0], 2)
            self.assertEqual(
                self.run_cli(["apply-game", "--project-file", str(project_file), "--yes"])[0],
                0,
            )
            self.assertEqual(conflict_file.read_text(encoding="utf-8").strip(), "patched sword model")

            manifests = sorted((root / ".modforge" / "manifests").glob("*.json"))
            self.assertEqual(len(manifests), 1)
            manifest_path = manifests[0]
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8"))["restored_at"], "")

            code, output = self.run_cli(
                [
                    "restore",
                    "--manifest",
                    str(manifest_path),
                    "--path",
                    conflict_path,
                    "--preview",
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            preview = json.loads(output)
            self.assertTrue(preview["can_restore"])
            self.assertEqual(preview["selected_paths"], [conflict_path])
            self.assertEqual(preview["restore_from_backup"], 1)
            self.assertEqual(conflict_file.read_text(encoding="utf-8").strip(), "patched sword model")
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8"))["restored_at"], "")

            self.assertEqual(
                self.run_cli(["restore", "--manifest", str(manifest_path), "--path", conflict_path])[0],
                2,
            )
            self.assertEqual(
                self.run_cli(
                    ["restore", "--manifest", str(manifest_path), "--path", conflict_path, "--yes", "--json"]
                )[0],
                0,
            )
            self.assertEqual(conflict_file.read_text(encoding="utf-8"), "original sword model")
            self.assertTrue(json.loads(manifest_path.read_text(encoding="utf-8"))["restored_at"])

    def test_cli_manifest_browser_and_project_portability_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            mods = root / "mods"
            project_file = root / "modforge.project.json"
            export_file = root / "export.json"
            import_dir = root / "imported"
            (mods / "Patch").mkdir(parents=True)
            game.mkdir()
            (mods / "Patch" / "new.txt").write_text("new", encoding="utf-8")

            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "init",
                        "--name",
                        "Portable",
                        "--game-root",
                        str(game),
                        "--mods-dir",
                        str(mods),
                        "--project-file",
                        str(project_file),
                    ]
                )[0],
                0,
            )
            self.assertEqual(self.run_cli(["apply-game", "--project-file", str(project_file), "--yes"])[0], 0)

            code, output = self.run_cli(["manifests", "list", "--project-file", str(project_file), "--json"])
            self.assertEqual(code, 0)
            manifest_list = json.loads(output)
            self.assertEqual(len(manifest_list), 1)
            manifest_id = manifest_list[0]["manifest_id"]
            self.assertTrue(manifest_list[0]["can_restore"])

            self.assertEqual(
                self.run_cli(["manifests", "latest", "--project-file", str(project_file), "--json"])[0],
                0,
            )
            code, output = self.run_cli(
                ["manifests", "show", manifest_id[:8], "--project-file", str(project_file), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["manifest_id"], manifest_id)

            self.assertEqual(
                self.run_cli(["project", "audit", "--project-file", str(project_file), "--json"])[0],
                0,
            )
            self.assertEqual(
                self.run_cli(
                    [
                        "project",
                        "export",
                        "--project-file",
                        str(project_file),
                        "--out",
                        str(export_file),
                    ]
                )[0],
                0,
            )
            export_payload = json.loads(export_file.read_text(encoding="utf-8"))
            self.assertFalse(export_payload["includes"]["game_files"])
            self.assertFalse(export_payload["includes"]["mod_files"])
            self.assertFalse(export_payload["includes"]["backup_files"])
            self.assertEqual(
                self.run_cli(["project", "import", str(export_file), "--target", str(import_dir)])[0],
                0,
            )
            self.assertTrue((import_dir / "modforge.project.json").exists())

    def test_cli_profile_catalog_validate_preview_import_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exported = root / "stellar.json"
            sample = root / "sample"
            custom_dir = root / "profiles"
            custom_profile = root / "custom.json"
            sample.mkdir()
            (sample / "CoolOutfit_P.pak").write_bytes(b"pak")
            (sample / "CoolOutfit_P.ucas").write_bytes(b"ucas")
            (sample / "CoolOutfit_P.utoc").write_bytes(b"utoc")
            custom_profile.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "custom-game",
                        "display_name": "Custom Game",
                        "deployment_rules": [
                            {
                                "id": "pak-to-mods",
                                "source_pattern": "*.pak",
                                "destination_root": "Mods",
                                "destination_pattern": "{filename}",
                            }
                        ],
                        "validation_samples": [
                            {
                                "source": "Example.pak",
                                "expected_destination": "Mods/Example.pak",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            code, output = self.run_cli(["profiles", "--json"])
            self.assertEqual(code, 0)
            self.assertIn("stellar-blade.experimental", [item["id"] for item in json.loads(output)])

            self.assertEqual(
                self.run_cli(["profiles", "export", "stellar-blade.experimental", "--out", str(exported)])[0],
                0,
            )
            self.assertTrue(exported.exists())
            self.assertEqual(self.run_cli(["profiles", "validate", str(exported), "--json"])[0], 0)

            code, output = self.run_cli(["profiles", "preview-map", str(exported), str(sample), "--json"])
            self.assertEqual(code, 0)
            preview = json.loads(output)
            destinations = [item["destination_path"] for item in preview["mappings"]]
            self.assertIn("SB/Content/Paks/~mods/CoolOutfit_P.pak", destinations)
            self.assertTrue(any(item["group_id"].startswith("unreal-sidecar:") for item in preview["mappings"]))

            self.assertEqual(
                self.run_cli(
                    [
                        "profiles",
                        "import",
                        str(custom_profile),
                        "--profile-dir",
                        str(custom_dir),
                        "--json",
                    ]
                )[0],
                0,
            )
            self.assertTrue((custom_dir / "custom-game.json").exists())


if __name__ == "__main__":
    unittest.main()
