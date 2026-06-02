# Apply Workflow Certification

This branch certifies the real apply and restore workflow with synthetic
fixtures only. Automated tests and smoke scripts must never touch a real game
installation.

## Scope

Covered:

- Apply to staging writes only to the configured staging directory.
- Apply to game is tested only against temporary fake game roots.
- Game apply creates manifests and backups before overwriting files.
- Restore preview is non-mutating.
- Selected restore touches only selected manifest entries.
- Full restore restores or removes manifest-tracked files.
- Enable/disable and priority changes affect the dry-run winner before apply.
- Project export/import preserves apply-relevant metadata without copying real
  game or mod payloads.
- REFramework/nativePC, Unreal sidecar, and Godot/STS2 families are exercised
  with synthetic fixtures.
- WinUI remains staging-first: destructive game apply and restore are not wired
  through the WinUI Python bridge.

Not covered or intentionally locked:

- WinUI game-folder apply.
- WinUI destructive restore.
- Real game installs.
- Real mod archives.
- Installer, bundled Python, Nexus integration, encrypted PAK support, asset
  editing, or virtual filesystem behavior.

## Commands

Run the full local gate:

```powershell
python -m unittest discover -s tests
python -m compileall -q src tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_smoke.ps1 -IncludeWinUI
git diff --check
```

Run the public-facing family apply/restore proof:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\family_apply_restore_smoke.ps1
```

That smoke creates temporary fake game roots for:

- `reframework_wilds` with `mhw-reframework`
- `unreal_pak` with `unreal-pak`
- `godot_sts2` with `sts2-mods`

Each case runs project init, scan, dry-run plan, apply-staging, apply-game,
manifest latest/show, restore preview, restore, and probe verification. The
REFramework case seeds an existing fake game file to prove backup/overwrite and
restore. Unreal and Godot/STS2 cases prove manifest-created files are removed by
restore.

## WinUI Gate

`scripts\smoke_winui_shell.ps1` checks that:

- no destructive `apply-game` or `restore` command is wired in
  `PythonCoreService`
- `MainWindow` does not call destructive game apply or restore bridge methods
- app startup does not launch a new Python process
- the WinUI executable starts and stays open

`scripts\smoke_winui_bridge_real.ps1` verifies the current staging-first bridge
contract through the CLI-equivalent workflow: project show, scan, enable/disable,
plan, priority reorder, and apply-staging. It does not unlock game apply.
