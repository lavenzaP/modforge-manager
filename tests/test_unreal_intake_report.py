from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bootstrap import ensure_src_path

ensure_src_path()

from modforge.core.game_profile import builtin_profile
from modforge.unreal.intake import build_unreal_intake_report


def write_file(root: Path, relative_path: str, payload: bytes = b"stub") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


class UnrealIntakeReportTests(unittest.TestCase):
    def test_unreal_intake_flat_sidecar_group_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "flat"
            for suffix in [".pak", ".ucas", ".utoc"]:
                write_file(source, f"CoolMod_P{suffix}")
            write_file(source, "CoolMod_P.json", b"{}")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            self.assertTrue(report.ok)
            self.assertEqual(report.package_shape, "flat_unreal_archive")
            self.assertEqual(len(report.sidecar_groups), 1)
            self.assertTrue(report.sidecar_groups[0].complete)
            destinations = {operation.source_path: operation.destination_path for operation in report.operations_preview}
            self.assertEqual(destinations["CoolMod_P.pak"], "SB/Content/Paks/~mods/CoolMod_P.pak")
            self.assertEqual(destinations["CoolMod_P.json"], "SB/Content/Paks/~mods/CoolMod_P.json")

    def test_unreal_intake_missing_sidecar_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "missing"
            write_file(source, "BrokenMod_P.pak")
            write_file(source, "BrokenMod_P.ucas")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            self.assertTrue(report.ok)
            self.assertEqual(report.sidecar_groups[0].missing_extensions, [".utoc"])
            self.assertTrue(any("missing .utoc" in warning for warning in report.warnings))

    def test_unreal_intake_preserves_rooted_sb_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "rooted"
            write_file(source, "SB/Content/Paks/~mods/Merged_P.pak")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)
            operation = report.operations_preview[0]

            self.assertEqual(operation.category, "already_rooted_sb_package")
            self.assertEqual(operation.destination_path, "SB/Content/Paks/~mods/Merged_P.pak")

    def test_unreal_intake_detects_ue4ss_runtime_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "runtime"
            write_file(source, "ue4ss/Mods/Cool/main.lua", b"print('ok')")
            write_file(source, "SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua", b"print('ok')")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)
            operations = {operation.source_path: operation for operation in report.operations_preview}

            self.assertEqual(operations["ue4ss/Mods/Cool/main.lua"].category, "ue4ss_runtime")
            self.assertEqual(
                operations["ue4ss/Mods/Cool/main.lua"].destination_path,
                "SB/Binaries/Win64/ue4ss/Mods/Cool/main.lua",
            )
            self.assertEqual(
                operations["SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua"].destination_path,
                "SB/Binaries/Win64/ue4ss/Mods/CNS/main.lua",
            )
            self.assertTrue(all(operation.high_risk for operation in operations.values()))

    def test_unreal_intake_marks_runtime_dll_high_risk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "dlls"
            write_file(source, "dwmapi.dll")
            write_file(source, "UE4SS.dll")
            write_file(source, "SB/Binaries/Win64/version.dll")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            self.assertEqual(len(report.high_risk_files), 3)
            self.assertTrue(all(operation.category == "runtime_dll" for operation in report.high_risk_files))
            self.assertTrue(all(operation.safety_tier == "dll-high-risk" for operation in report.high_risk_files))

    def test_unreal_intake_marks_logicmods_experimental(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "logicmods"
            write_file(source, "LogicMods/CoolLogic/Content/foo.uasset")
            write_file(source, "SB/Content/Paks/LogicMods/RootedLogic/foo.uasset")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            self.assertEqual({operation.category for operation in report.operations_preview}, {"logicmods_experimental"})
            self.assertTrue(any("LogicMods layout is experimental" in warning for warning in report.warnings))

    def test_unreal_intake_unknown_files_are_unmanaged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "unknown"
            write_file(source, "loose/random.bin")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            self.assertEqual(len(report.unmanaged_files), 1)
            self.assertEqual(report.unmanaged_files[0].source_path, "loose/random.bin")
            self.assertEqual(report.unmanaged_files[0].destination_path, "")

    def test_unreal_intake_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "readonly"
            write_file(source, "CoolMod_P.pak")
            before = sorted(path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file())

            build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), source)

            after = sorted(path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file())
            self.assertEqual(after, before)

    def test_unreal_intake_reads_zip_without_extracting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "sample.zip"
            with ZipFile(archive, "w") as zipped:
                zipped.writestr("CoolMod_P.pak", b"stub")
                zipped.writestr("CoolMod_P.ucas", b"stub")
                zipped.writestr("CoolMod_P.utoc", b"stub")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), archive)

            self.assertTrue(report.ok)
            self.assertEqual(report.source_kind, "zip")
            self.assertEqual(report.summary()["files"], 3)
            self.assertFalse((root / "CoolMod_P.pak").exists())

    def test_unreal_intake_zip_rejects_traversal_and_absolute_members(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "hostile.zip"
            hostile_members = [
                "../escape.pak",
                "/absolute/path.pak",
                "C:/Game/file.pak",
                "//server/share/file.pak",
                "SB/../escape.pak",
            ]
            with ZipFile(archive, "w") as zipped:
                for member in hostile_members:
                    zipped.writestr(member, b"stub")

            report = build_unreal_intake_report(builtin_profile("stellar-blade.experimental"), archive)

            self.assertFalse(report.ok)
            self.assertEqual(report.operations_preview, [])
            self.assertEqual(len(report.blocked), len(hostile_members))
            self.assertTrue(all("Unsafe zip member path" in item for item in report.blocked))
            self.assertFalse((root / "escape.pak").exists())


if __name__ == "__main__":
    unittest.main()
