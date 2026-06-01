# Game Profile Format

Game profiles describe how files from mod packages map into a game or staging
directory.

Initial fields:

- `id`: stable profile id.
- `display_name`: user-facing name.
- `game_root`: game installation root.
- `mods_dir`: source mod directory.
- `staging_dir`: dry-run or future deployment target.
- `deployment_rules`: file mapping rules.
- `ignored_patterns`: paths ignored during scanning.
- `supported_containers`: known package/container types.

The initial generic profile maps every loose mod file to the same relative path
under the staging directory.

## Built-In Profiles

- `generic-folder`: direct relative-path mapping.
- `mo2-mod`: Mod Organizer 2 style loose mod folders, ignoring `meta.ini`,
  `INI Tweaks/**`, and `.mohidden/**`.
- `godot-pck`: Godot/PCK workflow, mapping `.pck` files to `mods/`.
- `unreal-pak`: Unreal workflow, mapping `.pak`, `.ucas`, and `.utoc` files to
  `Content/Paks/~mods/`.
- `sts2-mods`: Slay the Spire 2 style mods folder, mapping packages under
  `mods/`.
- `reframework`: REFramework/nativePC style relative-path mapping.

Rules use `source_pattern` glob matching and `destination_root`/`destination_pattern`
for output paths. `**/` patterns also match files at the mod root.
