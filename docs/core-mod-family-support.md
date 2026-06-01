# Core Mod Family Support

## REFramework / NativePC

Profiles:

- `reframework`
- `mhw-reframework`

Supported workflow:

- Loose folders and ZIP packages.
- `reframework/**` and `nativePC/**` deployment roots for Wilds-style mods.
- Conflict detection for JSON/data files.
- Staging apply, game apply, manifest inspection, restore preview, and restore.
- Translation extraction from loose JSON/CSV/TXT files.

Not included:

- Runtime injection, DLL patching, or game-specific binary editing.

## Unreal PAK / UCAS / UTOC

Profile:

- `unreal-pak`

Supported workflow:

- Loose folders, ZIP packages, and top-level `.pak`, `.ucas`, `.utoc` archive
  packages.
- Mapping archive files to `Content/Paks/~mods/`.
- Warning when a `.pak/.ucas/.utoc` sidecar set is incomplete.
- Duplicate archive destination conflict detection.
- Archive-as-is deployment when `UnrealPak` is not configured.
- Optional extraction through a configured `unreal_pak` command template.

Not included:

- Encrypted PAK extraction.
- Asset editing inside `.pak`, `.ucas`, or `.utoc`.
- Repacking archives.

## Godot / Slay the Spire 2 PCK

Profiles:

- `godot-pck`
- `sts2-mods`

Supported workflow:

- Top-level `.pck` packages.
- Loose Godot-style mod folders.
- Mapping `.pck` files and loose mods into the game `mods/` folder.
- Duplicate `.pck` destination conflict detection.
- Archive-as-is deployment when `godot_pck_tool` is not configured.
- Optional extraction through a configured `godot_pck_tool` command template.
- Translation extraction from loose or extracted JSON/CSV/TXT files.

Not included:

- Custom binary PCK editing.
- PCK repacking.
- Engine-specific mod-loader behavior beyond safe file deployment.
