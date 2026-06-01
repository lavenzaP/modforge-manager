# Windows Shell Decision

## Milestone 6D Decision

WinUI 3 is the primary Windows shell candidate for ModForge Manager after the
6D polish pass.

Reasoning:

- WinUI 3 gives the app a more native Windows 11 direction.
- `NavigationView`, Fluent focus states, and modern controls fit the desired
  product feel better than the current WPF spike.
- The WinUI 3 shell now builds, copies required `.xbf` and `.pri` resources,
  and passes a launch smoke check.
- The same shared workflow state gates Home, Guided Setup, Mods, Plan, Apply &
  Restore, top actions, navigation readiness, and status text.

## Fallback Policy

Keep WPF as the fallback shell until WinUI packaging is proven beyond local
folder publish.

Do not remove yet:

- `desktop\ModForge.App`
- `scripts\build_windows_shell.ps1`
- `scripts\smoke_windows_shell.ps1`
- tkinter GUI entry points
- Python CLI/core

## Current Build Commands

Primary candidate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
powershell -ExecutionPolicy Bypass -File scripts\smoke_winui_shell.ps1
```

Fallback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_shell.ps1
powershell -ExecutionPolicy Bypass -File scripts\smoke_windows_shell.ps1
```

Full local smoke with both desktop shells:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release_smoke.ps1 -IncludeDesktop -IncludeWinUI
```

## Deferred

- Python bundling
- installer generation
- signing
- auto-update
- Rust helper components
- real sidecar process wiring
- new mod-family behavior
