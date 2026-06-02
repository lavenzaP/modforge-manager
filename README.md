# ModForge Manager

[한국어 README](README.ko.md)

ModForge Manager is a Windows-first desktop and CLI toolkit for organizing game
mod projects, scanning mod folders, previewing deployments, and generating safe
conflict reports.

The first version intentionally does not replace Mod Organizer 2, Vortex, or
Nexus Mods. It focuses on local project structure, dry-run planning, external
tool checks, and fake-fixture-tested core behavior.

## Current Status

Status: MVP release candidate, staging-first public preview.

The Python CLI/core is the tested backend. The WinUI 3 shell is the primary
Windows desktop candidate and uses a real Python bridge for supported actions:
create/load a project, scan mods, build a dry-run plan, enable/disable mods,
reorder priority, run read-only doctor/tool checks, and apply the winning plan
to a managed staging directory.

WinUI game-folder apply is intentionally locked for now. Game apply and restore
exist in the Python CLI/core, but the public desktop baseline is staging-first
until the GUI workflow is further hardened.

Python is not bundled, no installer is shipped, and the project does not provide
Nexus Mods downloads, encrypted PAK handling, DRM or anti-tamper bypass, asset
editing, archive repacking, or virtual filesystem behavior.

License note: this repository currently remains "All rights reserved" unless the
owner explicitly changes the license. Public visibility does not by itself make
the project open source.

## Current Scope

- Create and load a modding project file.
- Choose a built-in game profile template.
- Scan loose mod folders and ZIP mod packages.
- Extract PCK/PAK packages through configured external tools before scanning
  and deployment planning.
- Detect destination conflicts between enabled mods.
- Generate a dry-run deployment plan.
- Render a Markdown report.
- Check configured external tool paths from the CLI or GUI without failing the
  workflow.
- Create multiple user mod sets, switch between them, enable/disable mods, and
  set priority order per set.
- Copy winning files into a staging directory with an install manifest.
- Apply to the game root with backups, then restore all files or selected
  manifest paths.
- Extract basic JSON/CSV/TXT strings into a translation CSV.
- Provide a lightweight desktop GUI for creating/opening projects, scanning mods,
  toggling enabled state, changing priority, planning, reporting, applying, and
  restoring.
- Configure and check external tool paths from the GUI.
- Sort GUI mod tables, inspect scan warnings, and see progress/status updates
  during longer operations.
- Inspect manifests from the CLI, preview restores, and audit/export/import
  project metadata without copying real game or mod payloads.
- Run Windows smoke scripts for release-candidate checks.

## Public Preview Scope

The public desktop preview is staging-first:

1. Create or load a managed project.
2. Scan mods.
3. Generate a dry-run deployment plan.
4. Review conflicts and warnings.
5. Apply the winning plan to the project staging directory.

Staging apply writes only to the configured project staging directory. It does
not write to the game installation folder. Use the Python CLI for game
apply/restore workflows while the WinUI game-write path remains locked.

The WinUI bridge may run read-only `doctor --json` and `tools check --json`
through `PythonCoreService`. It must not wire `apply-game` or `restore` in the
WinUI bridge.

## MVP RC Target

The MVP release-candidate baseline certifies three core mod families:

- REFramework/nativePC mods, including Monster Hunter Wilds style layouts.
- Unreal `~mods` archive mods, including `.pak`, `.ucas`, and `.utoc` files.
- Godot/Slay the Spire 2 mods-folder workflows, including `.pck` files.

"Perfect support" for this MVP means safe local scan, plan, conflict report,
staging apply, game apply, manifest inspection, restore preview, restore,
doctor/audit checks, and documentation for synthetic fixtures in those families.
It does not mean Nexus downloads, encrypted PAK support, archive repacking,
arbitrary asset editing, a virtual filesystem, or installer generation.

Current freeze docs:

- [MVP status](docs/mvp-status.md)
- [Support matrix](docs/support-matrix.md)
- [Release checklist](docs/release-checklist.md)
- [Apply workflow certification](docs/apply-workflow-certification.md)
- [Changelog](CHANGELOG.md)
- [Architecture V2](docs/architecture-v2.md)
- [Windows shell plan](docs/windows-shell-plan.md)
- [Onboarding UX](docs/onboarding-ux.md)

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Run the installed entrypoints:

```powershell
modforge doctor
modforge profiles
modforge-gui
```

Run the CLI directly from the source tree without installing:

```powershell
$env:PYTHONPATH = "src"
python -m modforge doctor
python -m modforge --help
python -m modforge profiles
```

When no project file exists, `doctor` reports runtime checks plus a project-file
warning. Add `--strict` when warnings should fail automation.

Create a demo project:

```powershell
$env:PYTHONPATH = "src"
python -m modforge project init --name Demo --game-root tests\fixtures\fake_game --mods-dir tests\fixtures\fake_mods
python -m modforge project init --name STS2 --game-root C:\Games\STS2 --mods-dir C:\Games\STS2\mods --profile sts2-mods
python -m modforge scan-mods
python -m modforge plan
python -m modforge plan --summary
python -m modforge report --output .modforge\conflict-report.md
python -m modforge profile disable betterui
python -m modforge profile create boss-run --name "Boss Run" --copy-from default
python -m modforge profile switch boss-run
python -m modforge profile list
python -m modforge tools check
python -m modforge tools set unreal_pak "C:\Tools\UnrealPak.exe {archive} -Extract {output}"
python -m modforge doctor
python -m modforge apply-staging --yes
python -m modforge apply-game --yes
python -m modforge manifests list
python -m modforge manifests latest
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --preview
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --yes
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --path config\settings.json --yes
python -m modforge project audit
python -m modforge project export --out .modforge\project-export.json
python -m modforge translation extract --source tests\fixtures\fake_mods --output .modforge\strings.csv
```

Run the guided safe workflow on a temporary synthetic Monster Hunter Wilds /
REFramework fixture:

```powershell
$env:PYTHONPATH = "src"
$demo = Join-Path $env:TEMP ("modforge-safe-demo-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$game = Join-Path $demo "game"
$mods = Join-Path $demo "mods"
$project = Join-Path $demo "modforge.project.json"
$report = Join-Path $demo "conflict-report.md"

New-Item -ItemType Directory -Path $demo | Out-Null
Copy-Item -Recurse tests\fixtures\mhw_reframework_game $game
Copy-Item -Recurse tests\fixtures\mhw_reframework_mods $mods

python -m modforge doctor --project-file $project
python -m modforge project init --name "Wilds Demo" --game-root $game --mods-dir $mods --profile mhw-reframework --project-file $project
python -m modforge scan-mods --project-file $project
python -m modforge plan --project-file $project --summary
python -m modforge report --project-file $project --output $report

python -m modforge apply-staging --project-file $project
python -m modforge apply-staging --project-file $project --yes
python -m modforge apply-game --project-file $project
python -m modforge apply-game --project-file $project --yes

$manifest = Get-ChildItem (Join-Path $demo ".modforge\manifests") -Filter *.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --preview
python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --yes
```

Run the lightweight GUI:

```powershell
.\run_gui.bat
```

For a non-interactive runtime check:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_gui.ps1 -Check
```

The GUI intentionally uses the Python standard library `tkinter` for the first
usable version, so it can run in a fresh Python environment. On Windows the app
primes Tcl before creating the first Tk window, which avoids broken `init.tcl`
lookups in embedded or locally repaired Python installs.

Run the experimental Windows-first WPF shell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_shell.ps1
.\dist\ModForge.App\ModForge.App.exe
```

This shell is the Windows-first product-direction spike. It launches without
Python, shows guided onboarding and sample state data, and intentionally defers
real scan/plan/apply work until the sidecar bridge is wired in a later
milestone.

Run the WinUI 3 primary Windows shell candidate after installing .NET SDK 9:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
.\dist\ModForge.WinUI\ModForge.WinUI.exe
```

See `docs\windows-shell-decision.md` and `docs\winui3-comparison.md` for the
WinUI 3 decision and WPF fallback policy.

WinUI 3 is designed to avoid startup work: no startup scan, no Python process,
and no external tool probe until the user chooses an action. It can call the
Python core for the staging-first workflow listed above. Game apply remains
locked in the WinUI public preview so staging output can be inspected first.
The only WinUI diagnostics bridge additions are read-only `doctor --json` and
`tools check --json`; `apply-game` and `restore` stay CLI-only here.

Run the optional PySide6 GUI after installing the GUI extra:

```powershell
pip install -e ".[gui]"
modforge-gui-qt --check-dependency
modforge-gui-qt modforge.project.json
```

Built-in profile ids:

Certified core profiles:

- `reframework`
- `mhw-reframework`
- `unreal-pak`
- `godot-pck`
- `sts2-mods`

Additional templates:

- `generic-folder`
- `mo2-mod`
- `unity-bepinex`
- `unity-melonloader`
- `bethesda-data`
- `cyberpunk-2077`

Run tests with stdlib only:

```powershell
python -m unittest discover -s tests
python -m modforge doctor --project-file modforge.project.json
.\scripts\release_smoke.ps1
.\scripts\release_smoke.ps1 -IncludeDesktop
.\scripts\public_staging_smoke.ps1
```

Optional dev tooling after installing extras:

```powershell
.\scripts\dev_setup.ps1
pytest
python -m ruff check .
python -m ruff format --check .
.\scripts\lint.ps1
```

## Safety Defaults

- Dry-run by default.
- Staging apply writes only to the configured staging directory.
- The WinUI public preview keeps game-folder apply locked; inspect staging
  output first.
- WinUI may run read-only `doctor --json` and `tools check --json` through the
  Python bridge, but must not wire `apply-game` or `restore`.
- Game apply requires `--yes`, backs up overwritten files, and writes a manifest
  under `.modforge\manifests`.
- Restore requires `--yes` and a manifest path. Add one or more `--path`
  options to restore selected destination paths only.
- Restore preview works without `--yes`, reports blocked actions, and does not
  write files or update the manifest.
- ZIP entries with unsafe paths are ignored and reported as warnings.
- PCK/PAK extraction writes only under `.modforge\extracted` and the extracted
  files still pass through the same safe staging/game destination checks.
- Do not commit real game files, mod archives, crash dumps, DLLs, or executables.
- Use synthetic fixtures only.
- Unsupported containers fail with clear warnings.
