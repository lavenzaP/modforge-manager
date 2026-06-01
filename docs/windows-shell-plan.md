# Windows Shell Plan

## Purpose

Create a Windows-first desktop shell that feels like the product direction for
ModForge Manager, while the Python core continues to provide trusted behavior.

## Current Direction

Milestone 6D promotes `desktop\ModForge.WinUI` to the primary Windows shell
candidate. `desktop\ModForge.App` remains as the WPF fallback until WinUI
packaging, installer, and release distribution are proven.

## Milestone 6A Scope

Implement:

- `desktop/ModForge.App` WPF shell;
- modern dark navigation layout;
- Home, Guided Setup, Mods, Plan, Apply & Restore, and Tools screens;
- sample shell data;
- lazy `IPythonSidecarService`;
- build script that emits `dist\ModForge.App\ModForge.App.exe`;
- documentation for architecture and onboarding.

Do not implement:

- real Python sidecar invocation;
- Python bundling;
- installer generation;
- Rust helpers;
- removing the WPF fallback;
- new mod format behavior.

## Shell Structure

The shell is intentionally code-only WPF for this milestone so it can build on
the current machine without requiring a .NET SDK install.

Key files:

- `Program.cs`: application entry point and startup telemetry.
- `MainWindow.cs`: WPF layout and navigation.
- `Models.cs`: demo DTOs for project, mod rows, mod families, and steps.
- `Services.cs`: sidecar interface and fake implementation.
- `StartupTelemetry.cs`: startup timing and no-probe proof.

## Future Sidecar Flow

Future WPF commands should follow this pattern:

1. User clicks an explicit action.
2. WPF creates a cancellable operation.
3. Sidecar process starts only then.
4. Sidecar returns JSON progress and final result.
5. WPF updates progress, logs, and safe next action.

## Packaging

Current WPF fallback build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_shell.ps1
```

Output:

```text
dist\ModForge.App\ModForge.App.exe
```

Smoke check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_windows_shell.ps1
```

Current WinUI 3 candidate build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
```

Output:

```text
dist\ModForge.WinUI\ModForge.WinUI.exe
```

Smoke check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_winui_shell.ps1
```

Longer term, prove installer packaging, signing, and release distribution
before removing WPF or tkinter fallbacks.
