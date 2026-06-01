# Safety Model

ModForge Manager should make irreversible actions hard to trigger accidentally.

- Default to dry-run.
- Treat every game folder as user data.
- Generate a deployment plan before copying files.
- Write apply output only to staging until backup/restore for game folders is
  implemented and tested.
- Save an install manifest for staging writes.
- Ignore real binary payloads in Git.
- Keep tests on synthetic fixtures.

Unsupported formats should produce warnings, not partial writes.
