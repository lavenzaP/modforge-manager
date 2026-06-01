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

## Certified Core Mod Families

The MVP release-candidate support contract is documented in
`docs/core-mod-family-support.md`. The certified profile families are:

- REFramework/nativePC: `reframework`, `mhw-reframework`.
- Unreal `~mods`: `unreal-pak`.
- Godot/Slay the Spire 2: `godot-pck`, `sts2-mods`.

Other built-in profiles are useful templates, but they are not part of the MVP
certification baseline yet.

- `generic-folder`: direct relative-path mapping.
- `mo2-mod`: Mod Organizer 2 style loose mod folders, ignoring `meta.ini`,
  `INI Tweaks/**`, and `.mohidden/**`.
- `godot-pck`: Godot/PCK workflow, mapping `.pck` files to `mods/`.
- `unreal-pak`: Unreal workflow, mapping `.pak`, `.ucas`, and `.utoc` files to
  `Content/Paks/~mods/`.
- `sts2-mods`: Slay the Spire 2 style mods folder, mapping packages under
  `mods/`.
- `reframework`: REFramework/nativePC style relative-path mapping.
- `mhw-reframework`: Monster Hunter Wilds REFramework/nativePC workflow,
  allowing only `reframework/**` and `nativePC/**` package roots.
- `unity-bepinex`: Unity BepInEx workflow, mapping root DLLs to
  `BepInEx/plugins/` and common `plugins/`, `patchers/`, and `config/` folders
  under `BepInEx/`.
- `unity-melonloader`: Unity MelonLoader workflow, mapping root DLLs to `Mods/`
  while preserving `Mods/`, `Plugins/`, `UserData/`, `UserLibs/`, and
  `MelonLoader/` folders.
- `bethesda-data`: Bethesda Data folder workflow for plugin, BSA, asset, and
  script-extender style layouts, ignoring installer metadata such as `fomod/`.
- `cyberpunk-2077`: Cyberpunk 2077 workflow for REDmod/archive layouts,
  including root `.archive` files mapped to `archive/pc/mod/`.

Rules use `source_pattern` glob matching and `destination_root`/`destination_pattern`
for output paths. `**/` patterns also match files at the mod root.
