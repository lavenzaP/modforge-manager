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
