# Importing Mods

Fast path:

1. Drag a `.zip`, `.rar`, `.7z`, mod folder, or `.pak/.ucas/.utoc` file into
   ModForge Manager.
2. Turn the mod on or off.
3. Press `Apply Changes`.

Before importing an archive, you can use:

```text
More -> Check Mod Archive
```

That check extracts the archive to a temporary folder only. It does not change
game files or your ModForge mod library.

What ModForge does during import:

- Preserves README/install/changelog/license notes inside the imported mod.
- Shows `OK - instructions` when a selected mod has preserved notes.
- Uses the single wrapper folder as the final mod name when an archive contains
  exactly one top-level folder.
- Keeps duplicate mod names by creating a new folder such as `Name (2)` instead
  of deleting the old one.
- Writes `modforge-import.json` inside imported mod folders for troubleshooting.

Still limited:

- `.rar` and `.7z` support depends on Windows `tar.exe`.
- Password-protected or corrupt archives may need manual extraction.
- ModForge does not execute installers or scripts from archives.
