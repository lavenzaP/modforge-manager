# Release Checklist

Use this checklist before tagging an MVP release candidate.

## Version Sources

- `pyproject.toml`
- `src/modforge/__init__.py`
- `tests/test_packaging.py`

The current package version is `0.1.0`. The recommended MVP RC tag is
`v0.1.0-mvp-rc1`.

## Required Gates

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m compileall -q src tests
.\scripts\release_smoke.ps1
```

## Optional Desktop Shell Gate

The Milestone 6A WPF shell can be built and smoke-tested locally on Windows:

```powershell
.\scripts\release_smoke.ps1 -IncludeDesktop
.\scripts\smoke_windows_shell.ps1
```

The executable is written to:

```text
dist\ModForge.App\ModForge.App.exe
```

## Optional Lint Gate

Install development tooling first:

```powershell
.\scripts\dev_setup.ps1
```

Then run:

```powershell
.\scripts\lint.ps1
.\scripts\release_smoke.ps1 -IncludeLint
```

The lint gate uses `python -m ruff check .` and
`python -m ruff format --check .` so it does not modify files during release
validation.

## Tagging

Tag only after the required gates pass and the changelog/support matrix are
updated:

```powershell
git tag v0.1.0-mvp-rc1
git push origin v0.1.0-mvp-rc1
```

Do not tag if there are uncommitted changes, failing tests, or known release
blockers.
