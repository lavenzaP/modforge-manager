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

## MVP RC Hardening And Core Mod Families

- Re-consulted ChatGPT through Whale/CS WebLatch after the guided workflow
  foundation.
- Updated the Milestone 4 scope to MVP release-candidate hardening plus three
  certified core mod families: REFramework/nativePC, Unreal PAK/UCAS/UTOC, and
  Godot/Slay the Spire 2 PCK workflows.
- Added manifest browser helpers and CLI `manifests list/latest/show`.
- Added project metadata export/import/audit helpers and CLI commands.
- Added doctor audit output and health report writing.
- Added tkinter project health output.
- Added synthetic certification fixtures for the three core mod families.
- Added Windows PowerShell smoke scripts under `scripts/`.
- Added MVP RC, core mod family, project portability, and Windows smoke docs.
- Expanded tests from 54 to 66 stdlib `unittest` cases.

## MVP Freeze And Release Readiness

- Re-consulted ChatGPT through Whale/CS WebLatch after the MVP RC hardening
  commit and agreed that large MVP features are complete.
- Added release freeze docs: changelog, MVP status, support matrix, and release
  checklist.
- Hardened Windows smoke scripts so native command failures are checked
  explicitly and dev setup installs the `dev` extra.
- Added optional `scripts/lint.ps1` for `ruff check` and `ruff format --check`.
- Hardened deployment safety for linked package paths, linked source/destination
  components, unsafe ZIP absolute paths, and Windows case-insensitive conflicts.
- Fixed top-level Unreal sidecar archive deployment so `.pak/.ucas/.utoc` files
  with the same stem copy from their own source archive.
- Expanded restore selection for Unreal sidecar groups.
- Expanded tests from 66 to 76 stdlib `unittest` cases.

## Windows Shell Direction Spike

- Re-consulted ChatGPT through Whale/CS WebLatch after user feedback on
  onboarding, tkinter polish, Windows-first `.exe` delivery, and cold-start
  performance.
- Selected a WPF/C# shell as the next product direction while keeping the
  Python core as the source of truth.
- Added architecture, Windows shell, and onboarding UX docs.
- Added a code-only WPF shell under `desktop/ModForge.App` with sample shell data,
  guided setup, lazy sidecar policy, and startup telemetry.
- Added `scripts/build_windows_shell.ps1` to build
  `dist\ModForge.App\ModForge.App.exe` on the current Windows machine.

## Interactive Workflow UI Hardening

- Removed the vertical dry-run sidebar badge and replaced it with horizontal
  top-bar safety chips.
- Added a workflow state model from `NoProject` through `RestoreAvailable`.
- Gated top actions so Scan, Plan, and Confirm game apply unlock only after
  their prerequisites.
- Reworked Guided Setup into an interactive wizard with mod-family, folder,
  scan, plan review, staging, and game apply buttons.
- Removed milestone/debug wording from user-facing pages.
- Improved the Mods screen with dark DataGrid headers and a selected-mod detail
  panel.
- Expanded the Plan screen into a pre-apply review surface with conflict rows,
  warnings, a review checkbox, and staging unlock.
- Expanded Apply & Restore with staging, game confirm, manifest, and restore
  action zones.
- Rebuilt and smoke-tested the Windows shell executable.

## Workflow State Consistency Pass

- Reused the shared `WorkflowState` for sidebar readiness, top chips, top
  actions, Guided Setup, Plan, Apply & Restore, and the status bar.
- Changed Guided Setup steps to show completed, current, and locked states.
- Kept Plan review unchecked until the user manually confirms the review.
- Kept staging locked until Plan review is manually confirmed.
- Kept game apply locked until staging exists and the explicit confirmation
  checkbox is checked.
- Replaced static manifest placeholders with state-derived staging/game
  manifest labels.
- Made Restore Available prioritize View Manifest and Preview Restore instead
  of game apply.
- Switched WPF DataGrid columns to proportional sizing to avoid unnecessary
  horizontal scrollbars.

## WinUI 3 Comparison Spike

- Added `desktop\ModForge.WinUI`, a WinUI 3 comparison shell that mirrors the
  same guided workflow state gates as the WPF shell.
- Used WinUI `NavigationView` and `ListView` layouts to make the visual and
  control-stack differences easier to compare.
- Added `scripts\build_winui_shell.ps1` and `scripts\smoke_winui_shell.ps1`.
- Installed/verified .NET SDK 9.0.314 for the local WinUI build path.
- Restored Windows App SDK packages into repo-local cache folders and verified
  `dist\ModForge.WinUI\ModForge.WinUI.exe` with an execution smoke test.

## WinUI 3 Shell Decision & Polish Pass

- Promoted WinUI 3 to the primary Windows shell candidate while keeping WPF as
  the fallback until installer/release packaging is proven.
- Tightened WinUI empty states for NoProject, NoScan, NoPlan, and locked
  Apply & Restore paths.
- Improved path display with monospaced, ellipsized path rows.
- Reduced panel padding/header height and improved Guided Setup step badges.
- Improved ListView table readability with larger row text and trimmed cells.
- Added WinUI publish-file checks for `.exe`, `.dll`, `.pri`, and `.xbf`
  resources.
- Added `release_smoke.ps1 -IncludeWinUI` for the primary candidate shell.

## WinUI 3 Real Safe Bridge v1

- Discussed the next milestone with ChatGPT through Whale/CS WebLatch and
  selected a subprocess bridge to the existing Python CLI/core.
- Added `project show --json` so the Windows shell can load project metadata
  without parsing human-readable CLI output.
- Added a WinUI `PythonCoreService` that starts Python only on user actions and
  calls `project show`, `project init`, `scan-mods`, `plan`, and
  `apply-staging` through JSON/stdout contracts.
- Wired WinUI Open Project, Guided Setup folder selection/project creation,
  Scan Mods, Plan, manual Plan review, and Apply to staging to real Python core
  operations.
- Removed sample mod/conflict/warning data from the WinUI runtime path; Mods,
  Plan, KPIs, project summary, and staging manifest rows now use real command
  results.
- Fixed Guided Setup scan/replan row actions so they stay consistent with the
  top-bar actions and support rescanning/rebuilding plans.
- Reworked Plan conflicts from truncated table rows into detail cards with full
  destination paths, participating mods, source paths, kept/overwritten labels,
  and priority-based resolution buttons.
- Wired conflict resolution buttons to the existing `profile set-priority`
  command, then rescan/replan and relock staging review after priority changes.
- Wired selected-mod Enable/Disable actions to the existing profile state,
  then refresh scan results and relock/rebuild the dry-run plan when needed.
- Fixed `sts2-mods` loose-folder deployment so files preserve their mod folder
  under `mods/<package_name>/`; separate `mod_manifest.json` files no longer
  collide at `mods/mod_manifest.json`, and `.pck` files inside loose folders
  stay inside that folder.
- Kept game apply and destructive restore unwired and locked for this milestone.
- Added `scripts/smoke_winui_bridge_real.ps1` and included it in
  `release_smoke.ps1 -IncludeWinUI` to verify the project-load, scan, dry-run
  plan, priority reorder, and staging contract on fixture data without changing
  game files.

## Data-Driven Game Profiles v1

- Extended `GameProfile` with schema version, root aliases, rule ids, multi
  source patterns, sidecar groups, protected paths, validation samples, and
  safety tiers while preserving existing built-in profile ids.
- Added JSON profile loading plus custom profile import/export support.
- Added `profiles validate`, `profiles preview-map`, `profiles import`, and
  `profiles export` CLI commands.
- Added `stellar-blade.experimental`, a JSON profile for Stellar Blade/CNS
  archive sidecars, existing `SB/**` merge packages, and high-risk UE4SS/runtime
  file destinations.
- Updated deployment planning to record matched rule ids/safety tiers and warn
  on high-risk or protected destinations before any apply step.
- Added WinUI Guided Setup selection for the experimental Stellar Blade/CNS
  profile.

## Profile Picker UX

- Replaced the WinUI Guided Setup hard-coded mod family button row with a game
  profile picker backed by the Python `profiles --json` catalog.
- Kept a small built-in fallback catalog so Guided Setup can still render before
  Python is loaded, while catalog refresh happens only after a user action.
- Updated workflow labels from mod family selection to game profile selection so
  adding new profiles no longer widens the Guided Setup row.
- Updated Guided Setup so choosing a game folder creates or loads a managed
  project automatically under `Documents\ModForge Manager\Projects\<game>\`,
  with a default `Mods` folder and a separate `Change mods folder` action for
  users who want a custom source location.

## WinUI Tools/Doctor Read-Only Bridge

- Added script and documentation guardrails for the WinUI `PythonCoreService`
  bridge: read-only `doctor --json` and `tools check --json` are allowed, while
  `apply-game` and `restore` remain unwired from WinUI.

## Unreal-First Workbench v0

- Re-consulted ChatGPT through the existing Whale/ChatGPT thread and selected
  an Unreal-first workbench direction instead of adding more equal-priority game
  surfaces.
- Kept REFramework/nativePC and Godot/STS2 fixture support as regression
  coverage while making `unreal-pak` the primary profile candidate.
- Hardened the built-in `unreal-pak` profile with `family`, description, rule
  ids, archive safety tier, sidecar grouping, and validation samples.
- Added `translation inventory` to inspect staged output without mutating the
  game folder.
- Added translation inventory classification for JSON/CSV/TXT, Unreal
  `.locres/.locmeta`, staged `.pak/.ucas/.utoc` archives, and binary Unreal
  assets.
- Wired WinUI Apply & Restore to run the read-only localization inventory
  through `PythonCoreService` and display the candidate summary.
- Updated English/Korean README and workbench docs for the Unreal-first pivot.

## Unreal Intake / Stellar Blade CNS Hardening

- Added a read-only `unreal intake` CLI report for folders, ZIPs, or single
  package files before any real mod install test.
- Classified Stellar Blade/CNS style flat sidecar archives, rooted `SB/**`
  packages, UE4SS runtime folders, runtime DLL-like files, LogicMods candidates,
  and unmanaged files.
- Hardened `stellar-blade.experimental` so rooted UE4SS/runtime DLL paths are
  reviewed as high-risk instead of being hidden by broad `SB/**` mapping.
- Added synthetic temp-fixture tests and a smoke script for intake reporting
  without committing real mod archives.
