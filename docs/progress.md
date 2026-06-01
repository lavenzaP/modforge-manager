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
