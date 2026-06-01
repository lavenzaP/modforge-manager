# ModForge Manager

ModForge Manager is a Windows-first desktop and CLI toolkit for organizing game
mod projects, scanning mod folders, previewing deployments, and generating safe
conflict reports.

The first version intentionally does not replace Mod Organizer 2, Vortex, or
Nexus Mods. It focuses on local project structure, dry-run planning, external
tool checks, and fake-fixture-tested core behavior.

## Current Scope

- Create and load a modding project file.
- Scan loose mod folders and ZIP mod packages.
- Detect destination conflicts between enabled mods.
- Generate a dry-run deployment plan.
- Render a Markdown report.
- Check configured external tool paths without failing the workflow.
- Enable/disable mods and set a profile priority order.
- Copy winning files into a staging directory with an install manifest.
- Extract basic JSON/CSV/TXT strings into a translation CSV.
- Provide a lightweight desktop GUI shell while core logic remains testable
  without a GUI.

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
```

Create a demo project:

```powershell
$env:PYTHONPATH = "src"
python -m modforge.cli project init --name Demo --game-root tests\fixtures\fake_game --mods-dir tests\fixtures\fake_mods
python -m modforge.cli scan-mods
python -m modforge.cli plan
python -m modforge.cli report --output .modforge\conflict-report.md
python -m modforge.cli profile disable betterui
python -m modforge.cli tools check
python -m modforge.cli apply-staging --yes
python -m modforge.cli apply-game --yes
python -m modforge.cli restore --manifest .modforge\manifests\<manifest-id>.json --yes
python -m modforge.cli translation extract --source tests\fixtures\fake_mods --output .modforge\strings.csv
```

Run the lightweight GUI:

```powershell
$env:PYTHONPATH = "src"
python -m modforge.app
```

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
- Restore requires `--yes` and a manifest path.
- ZIP entries with unsafe paths are ignored and reported as warnings.
- Do not commit real game files, mod archives, crash dumps, DLLs, or executables.
- Use synthetic fixtures only.
- Unsupported containers fail with clear warnings.
