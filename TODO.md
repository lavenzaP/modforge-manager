# TODO

## Next

- Add a clearer conflict screen that shows the exact destination file, winner,
  loser, and the order change needed to switch the winner.
- Add per-game path rules for common Unreal layouts that do not use only
  `Content\Paks\~mods` and `Binaries\Win64`.
- Show skipped files in the main UI, not only in preview/issues popups.
- Add a simple "verify applied files" action that checks the latest manifest
  against the game folder.
- Make restore safer and more visible without bringing back a confusing
  top-level undo button.

## Mod Import

- Preserve archive readme/install notes somewhere visible after import.
- Detect archives that contain one extra wrapper folder and display the final
  mod name more cleanly.
- Add clearer errors when Windows cannot extract `.rar` or `.7z`.

## Game Profiles

- Let users rename game profiles.
- Let users remove stale game profiles.
- Detect Steam games from the installed app list instead of only folder picker.

## Release

- Add an installer or portable zip release workflow.
- Add screenshots after the UI settles.
- Keep README and Korean README in sync for each user-visible release.

## Later

- Nexus download/import support.
- Translation workflow.
- More detailed Unreal asset/pak validation.
- Optional advanced deployment modes such as hardlinks or symlinks.
