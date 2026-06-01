# Windows Release Smoke

The repository includes PowerShell smoke scripts for local release-candidate
checks. They do not build an installer or publish a release.

```powershell
.\scripts\run_tests.ps1
.\scripts\smoke_cli.ps1
.\scripts\smoke_gui_import.ps1
.\scripts\release_smoke.ps1
```

The GUI smoke imports the tkinter and optional Qt entry modules. If PySide6 is
not installed, the Qt dependency check prints guidance and the smoke continues
after confirming the import-gated path is safe.

Installer packaging, signing, auto-update, and public release publishing remain
deferred.
