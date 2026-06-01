# ModForge.App

Windows-first WPF shell prototype.

This is a WPF/C# desktop shell that launches without Python, shows a guided
first-run workflow, and uses sample state data until the Python sidecar bridge
is wired in a later milestone.

Build from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_shell.ps1
```

Output:

```text
dist\ModForge.App\ModForge.App.exe
```
