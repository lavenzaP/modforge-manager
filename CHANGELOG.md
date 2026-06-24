# Changelog

## Unreleased

- Reset the project to a Windows-first C# WinForms launcher.
- Removed the old Python backend, legacy GUI shells, old tests, and stale design docs from the active product path.
- Added standalone ModForge-owned mod state with `modforge-state.json`.
- Added per-game profiles and default game-specific mods folders.
- Added `.zip`, `.rar`, `.7z`, loose folder, and loose Unreal package import.
- Added basic Unreal package apply to `Content\Paks\~mods` plus simple UE4SS/runtime DLL placement.
- Added manifest-backed apply, reapply, restore, and hash-checked undo safety.
- Added Steam manifest detection so Steam games launch through `steam://rungameid/<appid>`.
- Improved conflict review so users can see the game file, copied mod, ignored mods, and how to change the winner.
- Replaced CI with Windows launcher smoke checks.
