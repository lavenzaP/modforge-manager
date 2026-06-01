# Support Matrix

This matrix describes the MVP freeze scope. "Certified" means the workflow has
synthetic fixtures and end-to-end tests for scan, plan, conflict report, staging
apply, game apply, manifest inspection, restore preview, restore, and docs.

| Family | Profiles | Containers | External Tool | Certified Workflow | Fixture |
| --- | --- | --- | --- | --- | --- |
| REFramework/nativePC | `reframework`, `mhw-reframework` | loose folders, ZIP | No | loose `reframework/` and `nativePC/` layouts | `tests/fixtures/mod_families/reframework_wilds` |
| Unreal `~mods` | `unreal-pak` | loose folders, ZIP, `.pak`, `.ucas`, `.utoc` | Optional `unreal_pak` extraction | archive-as-is deployment to `Content/Paks/~mods` | `tests/fixtures/mod_families/unreal_pak` |
| Godot/STS2 mods | `godot-pck`, `sts2-mods` | loose folders, ZIP, `.pck` | Optional `godot_pck_tool` extraction | archive-as-is deployment to `mods/` | `tests/fixtures/mod_families/godot_sts2` |
| Generic loose mods | `generic-folder` | loose folders, ZIP, optional PCK/PAK | Optional for PCK/PAK | local scan/plan/apply/restore | `tests/fixtures/fake_mods` |
| Additional templates | `mo2-mod`, Unity, Bethesda, Cyberpunk | loose folders, ZIP | No | deployment rule mapping tests | generated temp fixtures |

## Certified Guarantees

- Destination conflicts are detected using Windows case-insensitive path keys.
- Same-package case-only duplicate destinations are warned and reduced to one
  planned operation.
- Linked package paths and linked source/destination components are rejected or
  skipped before writes.
- ZIP entries with traversal, absolute, drive-prefixed, or UNC-like paths are
  ignored with warnings.
- Unreal sidecar restore selection expands `.pak/.ucas/.utoc` records that share
  the same destination base.

## Explicitly Not Supported

- Nexus Mods account flows, API downloads, or archive acquisition.
- Encrypted PAK extraction.
- Arbitrary asset editing, `.uasset` editing, or binary patching.
- Godot PCK or Unreal archive repacking.
- Full virtual filesystem behavior.
- Installer generation, signing, or auto-update.
