# Progress

## Initial Scaffold

- Private GitHub repository created first.
- Repository cloned before implementation.
- Initial plan requested from ChatGPT through the Whale/CS WebLatch flow.
- Scaffold focuses on safe core behavior, CLI, docs, and tests.

## First Usable CLI/GUI Pass

- Added active user profile state for disabled mods and priority order.
- Added external tool path configuration and checks.
- Added staging-only apply with `.modforge-install-manifest.json`.
- Added JSON/CSV/TXT translation extraction to CSV.
- Replaced the GUI placeholder with a lightweight tkinter project viewer.
- Expanded tests from 8 to 11 stdlib `unittest` cases.

## ZIP Package Support

- ZIP mod packages now produce file lists for scanning and dry-run plans.
- Staging apply can extract winning ZIP entries.
- Unsafe ZIP member paths are ignored with warnings.
- Expanded tests from 11 to 14 stdlib `unittest` cases.

## Game Apply And Restore

- Added `apply-game --yes` with backup and manifest creation.
- Added `restore --manifest <path> --yes` for manifest-based rollback.
- Project init now resolves the default `.modforge/staging` directory beside the
  project file.
- Expanded tests from 14 to 15 stdlib `unittest` cases.

## GUI Workflow Pass

- GUI can now create and open project files.
- GUI shows a sortable-style mod table with enabled state, priority, package
  type, file count, and warning count.
- GUI can enable/disable selected mods and move priorities up/down.
- GUI can plan, save reports, apply to staging, apply to game, and restore
  manifests through the same core functions used by the CLI.
- Expanded tests from 15 to 16 stdlib `unittest` cases.

## Built-In Game Profiles

- Added built-in profiles for generic folders, MO2 mod folders, Godot PCK,
  Unreal PAK, Slay the Spire 2 mods, and REFramework/nativePC style workflows.
- Added `modforge profiles` and `project init --profile <id>`.
- Deployment plans now honor profile `source_pattern`, `destination_root`,
  `ignored_patterns`, and `supported_containers`.
- GUI project creation prompts for a built-in profile id.
- Expanded tests from 16 to 20 stdlib `unittest` cases.

## GUI External Tools

- Added a GUI external tools dialog for configuring paths to 7-Zip, Godot PCK
  Tool, UnrealPak, and crash dump helpers.
- GUI tool checks use the same warning-only core checker as the CLI.
- Expanded tests from 20 to 21 stdlib `unittest` cases.

## User Mod Sets

- Added user profile management for multiple per-project mod sets.
- CLI can list, create, clone, switch, and delete user profiles.
- GUI can create, clone active, switch, and delete user profiles from a Profiles
  dialog.
- Active user profiles keep their own disabled mods and priority order.
- Expanded tests from 21 to 22 stdlib `unittest` cases.

## Selective Restore

- `restore_manifest` can now restore only selected destination paths.
- CLI `restore` accepts repeated `--path` options for partial rollback.
- GUI Restore now opens a manifest browser, shows restorable files, and supports
  restore-all or restore-selected flows.
- Expanded tests from 22 to 24 stdlib `unittest` cases.

## Expanded Game Profiles

- Added built-in profiles for Unity BepInEx, Unity MelonLoader, Bethesda Data
  folder/script extender layouts, and Cyberpunk 2077 REDmod/archive layouts.
- Added deployment-plan tests for each new profile template.
- Expanded tests from 24 to 28 stdlib `unittest` cases.

## External PCK/PAK Extraction

- Added external-tool backed extraction for `godot_pck` and `unreal_pak`
  packages.
- Project scans now use configured tool paths/templates and extract into
  `.modforge/extracted`.
- Staging/game apply can copy files from extracted PCK/PAK workspaces through
  the same safe destination checks as loose folders and ZIPs.
- Tool checks now understand command templates with `{archive}` and `{output}`.
- Expanded tests from 28 to 31 stdlib `unittest` cases.

## GUI Polish Pass

- Mod tables can now sort by name, enabled state, priority, package type, file
  count, or warning count.
- Scan output shows extracted package locations and per-package warnings.
- GUI scan, plan, report, apply, and restore actions now show progress/status
  updates and surface guarded error dialogs.
- Tool validation details now show the same OK/missing path information in the
  dialog as the output panel.
- Expanded tests from 31 to 33 stdlib `unittest` cases.

## Runtime Doctor And Entrypoints

- Added `modforge doctor` for runtime, project-file, profile, tkinter, tool-path,
  and safe scan smoke checks.
- Added JSON and strict modes for automation-friendly diagnostics.
- Added `python -m modforge` support and checks for packaged `modforge` and
  `modforge-gui` script declarations.
- Expanded tests from 33 to 40 stdlib `unittest` cases.

## Optional PySide6 UI

- Replaced the Qt placeholders with an import-gated PySide6 main window.
- Added `modforge-gui-qt` for Qt environments while keeping `modforge-gui` on
  the standard-library tkinter UI.
- The Qt UI can load projects, scan mods, render plans, save reports, apply to
  staging/game with confirmation, and show external tool checks through the same
  core workflow functions as the CLI.
- Added reusable Qt widget helpers for project summaries, mod tables, log output,
  and conflict summaries.
- Added dependency-check and model-helper tests that run even when PySide6 is
  not installed.
- Expanded tests from 40 to 44 stdlib `unittest` cases.

## Guided Safe Workflow Foundation

- Consulted ChatGPT through the Whale/CS WebLatch flow and selected Guided Safe
  Workflow V1 as the next milestone.
- Added `plan --summary` for compact risk, operation, conflict, and warning
  counts.
- Added `restore --preview` for no-write restore action previews.
- Hardened restore validation so selected-path mismatches, unsafe destinations,
  missing backups, and backup paths outside the manifest backup directory are
  blocked before writes.
- Added a Monster Hunter Wilds REFramework/nativePC synthetic fixture and
  profile tests.
- Updated the tkinter GUI restore path to preview and block unsafe restores.
- Added `docs/guided-workflow-v1.md`.
- Expanded tests from 44 to 54 stdlib `unittest` cases.
