# ModForge Manager

ModForge Manager is a Windows-first desktop and CLI toolkit for organizing game
mod projects, scanning mod folders, previewing deployments, and generating safe
conflict reports.

The first version intentionally does not replace Mod Organizer 2, Vortex, or
Nexus Mods. It focuses on local project structure, dry-run planning, external
tool checks, and fake-fixture-tested core behavior.

## Current Scope

- Create and load a modding project file.
- Scan loose mod folders and known container filenames.
- Detect destination conflicts between enabled mods.
- Generate a dry-run deployment plan.
- Render a Markdown report.
- Check configured external tool paths without failing the workflow.
- Keep GUI code thin while core logic remains testable without a GUI.

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
- Do not overwrite game folders in the initial scaffold.
- Do not commit real game files, mod archives, crash dumps, DLLs, or executables.
- Use synthetic fixtures only.
- Unsupported containers fail with clear warnings.
