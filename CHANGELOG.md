# Changelog

## v0.1.2-preview.1 - 2026-06-29

- Made the portable release self-contained so normal users do not need the .NET SDK or runtime.
- Added player-first quick start docs, Korean docs, release notes, and a release checklist.
- Added Steam game detection from installed app manifests, `Add Steam Game`, profile rename, and profile removal.
- Added safer archive import behavior with wrapper-folder cleanup, duplicate-name preservation, import metadata, preserved mod instructions, archive pre-check, and redacted diagnostic export.

## v0.1.1-preview.1 - 2026-06-29

- Reset the project to a Windows-first C# WinForms launcher.
- Removed the old Python backend, legacy GUI shells, old tests, and stale design docs from the active product path.
- Added standalone ModForge-owned mod state with `modforge-state.json`.
- Added per-game profiles and default game-specific mods folders.
- Added `.zip`, `.rar`, `.7z`, loose folder, and loose Unreal package import.
- Added basic Unreal package apply to `Content\Paks\~mods` plus simple UE4SS/runtime DLL placement.
- Added manifest-backed apply, reapply, restore, and hash-checked undo safety.
- Added a visible applied-file check against the latest apply manifest.
- Made restore preview safer by blocking restore when applied files changed or went missing.
- Show skipped files in the main mod list summary/status.
- Added a per-game PAK/UCAS/UTOC install folder override for Unreal games.
- Added Steam manifest detection so Steam games launch through `steam://rungameid/<appid>`.
- Added a portable zip packaging script with SHA256 output.
- Improved conflict review so users can see the game file, copied mod, ignored mods, and how to change the winner.
- Replaced CI with Windows launcher smoke checks.
