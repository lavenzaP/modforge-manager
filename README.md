# ModForge Manager

[Korean README](README.ko.md)

ModForge Manager is a small Windows mod manager for Unreal Engine games.

It is currently focused on the basic loop that has to work before anything
else: add mods, turn them on or off, apply the current list to the game folder,
and launch the game through Steam when possible.

## Quick Start

For normal users:

1. Download `ModForge.Manager-v0.1.2-preview.1-win-x64.zip` from
   [Releases](https://github.com/lavenzaP/modforge-manager/releases).
   Do not download `Source code` unless you want to build the app yourself.
2. Extract the zip anywhere.
3. Run `ModForge.Launcher.exe`.
4. Use `More` -> `Add Steam Game`, or choose your Unreal game folder manually.
5. Drag mod archives, mod folders, or `.pak/.ucas/.utoc` files into the app,
   turn mods on or off, then press `Apply Changes`.

The release zip is self-contained. You do not need Visual Studio, the .NET SDK,
or a build step to try it.

This preview has no installer yet. Windows SmartScreen may warn because the app
is unsigned. Normal use should not require administrator rights unless your game
folder itself blocks writes.

Safety basics:

- ModForge stores its own mod library beside the executable.
- `Apply Changes` only writes the currently enabled mods.
- `Check Applied Mods` verifies files from the latest ModForge apply.
- `Restore Last Apply` refuses to restore when files changed outside ModForge.

## Current Status

This repository is being rebuilt around a simple C# WinForms launcher.

Working today:

- Add loose `.pak`, `.ucas`, and `.utoc` files.
- Add `.zip`, `.rar`, and `.7z` archives by extracting them into the selected
  game's ModForge mods folder.
- Add already-extracted mod folders by drag and drop.
- Check mod archives before import without changing game or mod library files.
- Preserve README/install notes from imported archives and folders.
- Clean up one-wrapper-folder archives into a clearer final mod folder name.
- Enable, disable, reorder, and search mods.
- Store enabled state and priority in `modforge-state.json`.
- Keep separate mod libraries per game profile.
- Add installed Steam Unreal games from app manifests when they can be detected.
- Rename or remove game profiles without deleting game or mod files.
- Apply enabled Unreal package mods to `<Project>\Content\Paks\~mods`.
- Change the PAK/UCAS/UTOC install folder per game when an Unreal game uses a
  different folder.
- Apply simple UE4SS/runtime DLL layouts to `<Project>\Binaries\Win64`.
- Check applied files against the latest ModForge manifest.
- Restore the latest ModForge apply with hash-checked manifests.
- Show conflicts and skipped files before apply.
- Export a redacted diagnostic report for troubleshooting.
- Launch Steam games through `steam://rungameid/<appid>` when the Steam
  manifest can be detected.
- Build a self-contained portable release zip.

Not working yet:

- Nexus downloads.
- Native installer with Start Menu shortcuts and uninstall support.
- Advanced conflict review UI.
- PAK repacking or encrypted PAK editing.
- Full translation editor.
- Virtual file system, hardlink, or symlink deployment.

## Default Paths

Game profiles are saved next to the launcher executable:

```text
<ModForge folder>\games.json
```

Each game gets a default mods folder like this:

```text
<ModForge folder>\Games\<Game Name>\Mods
```

Apply manifests and backups live next to that game's mods folder:

```text
<ModForge folder>\Games\<Game Name>\.modforge
```

## Build For Developers

Requirements:

- Windows
- .NET 9 SDK

Build the launcher for development:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_launcher.ps1
```

Output:

```text
dist\ModForge.Launcher\ModForge.Launcher.exe
```

## Smoke Test For Developers

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

The smoke test builds the launcher, runs the built-in self-test, and scans a
temporary ModForge mods folder without touching real game files.

## Portable Package

Build a self-contained portable zip:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_launcher.ps1
```

Output:

```text
dist\ModForge.Manager-v0.1.2-preview.1-win-x64.zip
```

Extract the zip anywhere and run `ModForge.Launcher.exe`. Game profiles,
ModForge mod folders, manifests, and backups are stored beside the executable.

## Agent Workflow

Use [docs/agent-pipeline.md](docs/agent-pipeline.md) for scoped agent work,
beginner-user review, safety review, and release checks.

## CLI Checks For Developers

Scan a mods folder:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --smoke --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

Apply enabled mods:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --apply --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

Undo the latest apply:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --undo --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

Verify the latest apply:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --verify --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

## Safety Model

`Apply Changes` first restores the previous ModForge apply when one exists,
then writes the currently enabled mods. Files are restored or deleted only when
they still match the previous ModForge manifest. If a game file was changed by
something else, ModForge refuses to overwrite that uncertainty silently.

`Check Applied Mods` verifies that files from the latest ModForge apply are
still present and unchanged. `Restore Last Apply` is blocked when those files
changed or went missing.

## Repository Shape

The active app is intentionally small:

```text
desktop/ModForge.Launcher/
scripts/build_launcher.ps1
scripts/package_launcher.ps1
scripts/smoke_launcher.ps1
```

Older Python, WPF, and WinUI experiments have been removed from the active
product path.

## License

MIT. See [LICENSE](LICENSE).
