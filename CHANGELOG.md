# Changelog

## Unreleased

### Public Readiness

- Added public-readiness documentation for the staging-first public preview.
- Added SECURITY and CONTRIBUTING guidance that blocks real game/mod assets,
  generated binaries, crash dumps, private logs, and bypass requests.
- Added GitHub Actions CI for Python unit tests, compile checks, and the public
  staging smoke.
- Added a public staging smoke script that verifies scan, dry-run plan,
  apply-staging, staging manifest creation, and no game-folder writes.
- Clarified README status in English and Korean: Python CLI/core is the tested
  backend, WinUI 3 is the primary shell candidate with a real Python bridge,
  and WinUI game apply is intentionally locked in the public preview.
- Split the Korean README into `README.ko.md` so the GitHub landing README stays
  English-first while Korean users still get a full local guide.

### Development

- Harden Windows release smoke scripts so native command failures stop the run.
- Add release-readiness safety coverage for case-insensitive path conflicts,
  linked paths, ZIP absolute paths, and Unreal sidecar restore selection.
- Add MVP freeze support matrix and release checklist docs.
- Add an experimental WPF/C# Windows shell with guided onboarding, sample shell
  data, lazy sidecar policy, and a local `.exe` build script.
- Harden the WPF shell with workflow-state action gating, interactive guided
  setup buttons, dark table styling, selected-mod details, plan review gates,
  and apply/restore action zones.
- Add a WPF workflow-state consistency pass so Plan review, staging, game
  apply, restore, manifests, top actions, and status labels share the same
  state source.
- Add a WinUI 3 comparison shell scaffold with the same workflow-state gates,
  plus build/smoke scripts that explain the required .NET SDK and Windows App
  SDK toolchain.
- Promote WinUI 3 to the primary Windows shell candidate while retaining WPF as
  fallback, with tighter empty states, path formatting, table readability, and
  publish-file checks.

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
- The WPF shell is still a direction spike; real Python sidecar calls are
  deferred, but the Milestone 6C UI now behaves like a state-consistent gated
  workflow shell instead of a static description.
