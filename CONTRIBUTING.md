# Contributing

ModForge Manager is currently a small Windows-first C# WinForms launcher.

Before sending changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

Keep changes boring:

- Prefer the existing `desktop/ModForge.Launcher` project unless there is a real reason to split.
- Keep file writes manifest-bound and undoable.
- Keep user state in ModForge-owned files such as `modforge-state.json`.
- Do not reintroduce Python, WPF, WinUI, Rust, or new dependencies without a clear decision.
- Do not commit real mod archives, game files, DLLs, EXEs, crash dumps, or generated release output.
