# Windows Release Smoke

The repository includes PowerShell smoke scripts for local release-candidate
checks. They do not build an installer or publish a release.

```powershell
.\scripts\run_tests.ps1
.\scripts\smoke_cli.ps1
.\scripts\smoke_gui_import.ps1
.\scripts\release_smoke.ps1
.\scripts\release_smoke.ps1 -IncludeDesktop
.\scripts\release_smoke.ps1 -IncludeWinUI
.\scripts\release_smoke.ps1 -IncludeDesktop -IncludeWinUI
.\scripts\smoke_windows_shell.ps1
.\scripts\smoke_winui_shell.ps1
```

The GUI smoke imports the tkinter and optional Qt entry modules. If PySide6 is
not installed, the Qt dependency check prints guidance and the smoke continues
after confirming the import-gated path is safe.

The WPF fallback smoke builds and briefly opens
`dist\ModForge.App\ModForge.App.exe`.

The WinUI 3 candidate smoke builds, checks required publish files
(`.exe`, `.dll`, `.pri`, `.xbf`), and briefly opens
`dist\ModForge.WinUI\ModForge.WinUI.exe`.

Both desktop shells are expected to launch without Python and close cleanly
during the smoke check.

Installer packaging, signing, auto-update, and public release publishing remain
deferred.
