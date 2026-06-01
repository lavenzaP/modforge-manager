# Changelog

## Unreleased

- Harden Windows release smoke scripts so native command failures stop the run.
- Add release-readiness safety coverage for case-insensitive path conflicts,
  linked paths, ZIP absolute paths, and Unreal sidecar restore selection.
- Add MVP freeze support matrix and release checklist docs.

## 0.1.0 MVP RC

### Added

- CLI and tkinter GUI project workflows.
- Built-in profiles for certified REFramework/nativePC, Unreal `~mods`, and
  Godot/Slay the Spire 2 mod families.
- Loose folder, ZIP, Godot PCK, and Unreal PAK/UCAS/UTOC package scanning.
- Dry-run deployment plans, conflict reports, staging apply, game apply,
  backup manifests, restore preview, and restore.
- Manifest list/latest/show commands.
- Project export/import/audit and doctor health reports.
- Basic JSON/CSV/TXT translation extraction.
- Optional PySide6 GUI entrypoint.

### Safety

- Dry-run behavior is the default.
- Game writes require `--yes`.
- Overwritten game files are backed up before replacement.
- Restores are manifest-bound and can be previewed before writing.
- Unsafe ZIP member paths and unsafe restore destinations are blocked.

### Known Limitations

- No Nexus Mods login, API, or downloads.
- No encrypted PAK extraction.
- No arbitrary `.uasset` editing.
- No Godot PCK or Unreal archive repacking.
- No virtual filesystem or MO2/Vortex replacement layer.
- No installer, signing, auto-update, or public package publishing yet.
