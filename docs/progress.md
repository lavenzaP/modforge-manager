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
