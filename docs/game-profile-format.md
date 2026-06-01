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
