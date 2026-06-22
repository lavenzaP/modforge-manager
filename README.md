# ModForge Manager

[Korean README](README.ko.md)

ModForge Manager is a small Windows mod manager for Unreal Engine games.

It is currently focused on the basic loop that has to work before anything
else: add mods, turn them on or off, apply the current list to the game folder,
and launch the game through Steam when possible.

## Current Status

This repository is being rebuilt around a simple C# WinForms launcher.

Working today:

- Add loose `.pak`, `.ucas`, and `.utoc` files.
- Add `.zip`, `.rar`, and `.7z` archives by extracting them into the selected
  game's ModForge mods folder.
- Add already-extracted mod folders by drag and drop.
- Enable, disable, reorder, and search mods.
- Store enabled state and priority in `modforge-state.json`.
- Keep separate mod libraries per game profile.
- Apply enabled Unreal package mods to `<Project>\Content\Paks\~mods`.
- Apply simple UE4SS/runtime DLL layouts to `<Project>\Binaries\Win64`.
- Undo the latest ModForge apply with hash-checked manifests.
- Launch Steam games through `steam://rungameid/<appid>` when the Steam
  manifest can be detected.

Not working yet:

- Nexus downloads.
- Installer packaging.
- Advanced conflict review UI.
- PAK repacking or encrypted PAK editing.
- Full translation editor.
- Virtual file system, hardlink, or symlink deployment.

## Default Paths

Game profiles are saved here:

```text
%APPDATA%\ModForge Manager\games.json
```

Each game gets a default mods folder like this:

```text
%USERPROFILE%\Documents\ModForge Manager\Games\<Game Name>\Mods
```

Apply manifests and backups live next to that game's mods folder:

```text
%USERPROFILE%\Documents\ModForge Manager\Games\<Game Name>\.modforge
```

## Build

Requirements:

- Windows
- .NET 9 SDK

Build the launcher:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_launcher.ps1
```

Output:

```text
dist\ModForge.Launcher\ModForge.Launcher.exe
```

## Smoke Test

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

The smoke test builds the launcher, runs the built-in self-test, and scans a
temporary ModForge mods folder without touching real game files.

## CLI Checks

Scan a mods folder:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --smoke --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

Apply enabled mods:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --apply --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

Undo the latest apply:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --undo --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

## Safety Model

`Apply Changes` first restores the previous ModForge apply when one exists,
then writes the currently enabled mods. Files are restored or deleted only when
they still match the previous ModForge manifest. If a game file was changed by
something else, ModForge refuses to overwrite that uncertainty silently.

## Repository Shape

The active app is intentionally small:

```text
desktop/ModForge.Launcher/
scripts/build_launcher.ps1
scripts/smoke_launcher.ps1
```

Older Python, WPF, and WinUI experiments have been removed from the active
product path.

## License

MIT. See [LICENSE](LICENSE).
