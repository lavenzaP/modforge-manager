# ModForge Manager

ModForge Manager is a Windows-first desktop and CLI toolkit for organizing game
mod projects, scanning mod folders, previewing deployments, and generating safe
conflict reports.

The first version intentionally does not replace Mod Organizer 2, Vortex, or
Nexus Mods. It focuses on local project structure, dry-run planning, external
tool checks, and fake-fixture-tested core behavior.

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

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Run the CLI directly from the source tree without installing:

```powershell
$env:PYTHONPATH = "src"
python -m modforge.cli --help
python -m modforge.cli profiles
```

Create a demo project:

```powershell
$env:PYTHONPATH = "src"
python -m modforge.cli project init --name Demo --game-root tests\fixtures\fake_game --mods-dir tests\fixtures\fake_mods
python -m modforge.cli project init --name STS2 --game-root C:\Games\STS2 --mods-dir C:\Games\STS2\mods --profile sts2-mods
python -m modforge.cli scan-mods
python -m modforge.cli plan
python -m modforge.cli report --output .modforge\conflict-report.md
python -m modforge.cli profile disable betterui
python -m modforge.cli profile create boss-run --name "Boss Run" --copy-from default
python -m modforge.cli profile switch boss-run
python -m modforge.cli profile list
python -m modforge.cli tools check
python -m modforge.cli tools set unreal_pak "C:\Tools\UnrealPak.exe {archive} -Extract {output}"
python -m modforge.cli apply-staging --yes
python -m modforge.cli apply-game --yes
python -m modforge.cli restore --manifest .modforge\manifests\<manifest-id>.json --yes
python -m modforge.cli restore --manifest .modforge\manifests\<manifest-id>.json --path config\settings.json --yes
python -m modforge.cli translation extract --source tests\fixtures\fake_mods --output .modforge\strings.csv
```

Run the lightweight GUI:

```powershell
$env:PYTHONPATH = "src"
python -m modforge.app
```

The GUI intentionally uses the Python standard library `tkinter` for the first
usable version, so it can run before optional PySide6 work begins.

Built-in profile ids:

- `generic-folder`
- `mo2-mod`
- `godot-pck`
- `unreal-pak`
- `sts2-mods`
- `reframework`
- `unity-bepinex`
- `unity-melonloader`
- `bethesda-data`
- `cyberpunk-2077`

Run tests with stdlib only:

```powershell
python -m unittest discover -s tests
```

Optional dev tooling after installing extras:

```powershell
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
```

## Safety Defaults

- Dry-run by default.
- Staging apply writes only to the configured staging directory.
- Game apply requires `--yes`, backs up overwritten files, and writes a manifest
  under `.modforge\manifests`.
- Restore requires `--yes` and a manifest path. Add one or more `--path`
  options to restore selected destination paths only.
- ZIP entries with unsafe paths are ignored and reported as warnings.
- PCK/PAK extraction writes only under `.modforge\extracted` and the extracted
  files still pass through the same safe staging/game destination checks.
- Do not commit real game files, mod archives, crash dumps, DLLs, or executables.
- Use synthetic fixtures only.
- Unsupported containers fail with clear warnings.
