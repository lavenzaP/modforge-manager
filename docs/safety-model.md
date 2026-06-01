# Safety Model

ModForge Manager should make irreversible actions hard to trigger accidentally.

- Default to dry-run.
- Treat every game folder as user data.
- Generate a deployment plan before copying files.
- Write staging output only to the configured staging directory.
- Require explicit `--yes` for game-root writes.
- Back up overwritten game-root files before replacement.
- Save install manifests for staging and game-root writes.
- Restore game-root writes through a saved manifest.
- Ignore real binary payloads in Git.
- Keep tests on synthetic fixtures.

Unsupported formats should produce warnings, not partial writes.
