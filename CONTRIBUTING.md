# Contributing

ModForge Manager is in an MVP release-candidate phase. Contributions should keep
the project safe, small, and testable.

## Ground Rules

- Use synthetic fixtures only.
- Do not commit real game files, real mod archives, crash dumps, logs, or
  generated binaries.
- Do not bundle third-party external tools.
- Do not add code for DRM, anti-tamper, account, or encryption bypass.
- Keep write operations dry-run-first, staging-first, and manifest-bound.
- Keep public wording honest: this is not an MO2/Vortex replacement.

## Before Opening a Pull Request

Run the relevant checks:

```powershell
python -m unittest discover -s tests
python -m compileall -q src tests
powershell -ExecutionPolicy Bypass -File scripts\public_staging_smoke.ps1
git diff --check
```

If you changed linted Python code and the dev dependencies are installed, also
run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\lint.ps1
```

## Fixture Policy

Fixtures must be fake and minimal. If a test needs an engine-like extension,
prefer a tiny synthetic file under `tests/fixtures` and document why it exists.
Do not copy files from an installed game or downloaded mod.

