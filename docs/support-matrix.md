# Support Matrix

This matrix describes the tested compatibility baseline. The product direction
has shifted to an Unreal-first workbench, but the older REFramework/nativePC and
Godot/STS2 fixtures remain as regression coverage. "Certified" means the Python
CLI/core workflow has synthetic fixtures and end-to-end tests for scan, plan,
conflict report, staging apply, game apply, manifest inspection, restore
preview, restore, and docs. The WinUI public preview is staging-first and keeps
game-folder apply locked while the desktop workflow is hardened.

| Family | Profiles | Containers | External Tool | Certified Workflow | Fixture |
| --- | --- | --- | --- | --- | --- |
| REFramework/nativePC | `reframework`, `mhw-reframework` | loose folders, ZIP | No | loose `reframework/` and `nativePC/` layouts | `tests/fixtures/mod_families/reframework_wilds` |
| Unreal `~mods` | `unreal-pak` | loose folders, ZIP, `.pak`, `.ucas`, `.utoc` | Optional `unreal_pak` extraction | archive-as-is deployment to `Content/Paks/~mods`; staged localization inventory | `tests/fixtures/mod_families/unreal_pak` |
| Godot/STS2 mods | `godot-pck`, `sts2-mods` | loose folders, ZIP, `.pck` | Optional `godot_pck_tool` extraction | standalone `.pck` deployment to `mods/`; loose folders preserved under `mods/<package_name>/` | `tests/fixtures/mod_families/godot_sts2` |
| Stellar Blade / CNS | `stellar-blade.experimental` | loose folders, ZIP, `.pak`, `.ucas`, `.utoc` | Optional `unreal_pak` extraction | experimental JSON profile; read-only intake report for `~mods`, `SB/**`, UE4SS/runtime, LogicMods, sidecar groups, and unmanaged files | generated temp fixtures |
| Generic loose mods | `generic-folder` | loose folders, ZIP, optional PCK/PAK | Optional for PCK/PAK | local scan/plan/apply/restore | `tests/fixtures/fake_mods` |
| Additional templates | `mo2-mod`, Unity, Bethesda, Cyberpunk | loose folders, ZIP | No | deployment rule mapping tests | generated temp fixtures |

## Certified Guarantees

- Destination conflicts are detected using Windows case-insensitive path keys.
- Real staging copies winning operations into the configured staging directory
  and writes a staging install manifest without mutating the game folder.
- Same-package case-only duplicate destinations are warned and reduced to one
  planned operation.
- Linked package paths and linked source/destination components are rejected or
  skipped before writes.
- ZIP entries with traversal, absolute, drive-prefixed, or UNC-like paths are
  ignored with warnings.
- Unreal sidecar restore selection expands `.pak/.ucas/.utoc` records that share
  the same destination base.
- Translation inventory can inspect staged output without mutating the game
  folder and classify JSON/CSV/TXT, `.locres/.locmeta`, Unreal archives, and
  binary Unreal assets.
- Unreal intake reports can inspect folders, ZIPs, or single files without
  extracting or writing, then classify Stellar Blade/CNS style archive sidecars,
  rooted `SB/**` packages, UE4SS runtime folders, runtime DLL-like files,
  LogicMods candidates, and unmanaged files.
- Custom game profiles can be validated and previewed before use, and unsafe
  absolute/traversal destinations are rejected.

## Explicitly Not Supported

- Nexus Mods account flows, API downloads, or archive acquisition.
- Encrypted PAK extraction.
- Arbitrary asset editing, `.uasset` editing, or binary patching.
- Godot PCK or Unreal archive repacking.
- Full virtual filesystem behavior.
- Installer generation, signing, or auto-update.
