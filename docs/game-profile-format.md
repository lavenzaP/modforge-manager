# Game Profile Format

Game profiles describe how files from mod packages map into a game or staging
directory.

Project files still store `game_root`, `mods_dir`, and `staging_dir`, but a
game profile itself is now a data-driven mapping contract. Profile JSON files
can be validated, previewed, imported, and exported through the CLI before they
are used by a project.

Core profile fields:

- `id`: stable profile id.
- `display_name`: user-facing name.
- `schema_version`: profile schema version, currently `1`.
- `family`: optional broad family such as `unreal`, `reframework`, or `godot`.
- `root_aliases`: named relative destination roots such as `mods_paks` or
  `binaries_win64`.
- `deployment_rules`: file mapping rules.
- `ignored_patterns`: paths ignored during scanning.
- `supported_containers`: known package/container types.
- `sidecar_groups`: optional atomic file groups, such as Unreal
  `.pak/.ucas/.utoc` sets.
- `protected_paths`: paths that should trigger warning/extra review.
- `validation_samples`: source-to-destination examples used by validation.

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
- `stellar-blade.experimental`: experimental Stellar Blade/CNS profile loaded
  from JSON. It maps Unreal archive sidecars to `SB/Content/Paks/~mods`,
  preserves existing `SB/**` package layouts, and marks UE4SS/runtime DLL writes
  under `SB/Binaries/Win64` as high risk.

Rules use `source_pattern` or `source_patterns` glob matching and
`destination_root`/`destination_pattern` for output paths. `destination_root`
can be either a literal relative path or a key from `root_aliases`.
`destination_pattern` can reference `{relative_path}`, `{filename}`, `{stem}`,
`{package_id}`, and `{package_name}`. `container_types` and
`exclude_container_types` can narrow a rule to archive-as-is packages or loose
folders. `**/` patterns also match files at the mod root.

Custom profile files must keep every destination relative to the game root.
Absolute paths, drive paths, UNC paths, and `..` traversal are rejected by
validation. Custom profiles do not support arbitrary script hooks, registry
edits, post-install commands, or executable patching.

Useful CLI commands:

```powershell
python -m modforge profiles export stellar-blade.experimental --out stellar.json
python -m modforge profiles validate stellar.json --json
python -m modforge profiles preview-map stellar.json .\SampleMod --json
python -m modforge profiles import .\my-profile.json
```

For `sts2-mods`, loose folder mods preserve their package directory under
`mods/`, so separate mods with their own `mod_manifest.json` files map to
`mods/<package_name>/mod_manifest.json` instead of colliding at
`mods/mod_manifest.json`. Standalone `.pck` package files still deploy directly
under `mods/`; `.pck` files inside a loose mod folder stay inside that folder.
