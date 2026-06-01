# Safety Model

ModForge Manager should make irreversible actions hard to trigger accidentally.

- Default to dry-run.
- Treat every game folder as user data.
- Generate a deployment plan before copying files.
- Require an install manifest before apply/restore features are added.
- Ignore real binary payloads in Git.
- Keep tests on synthetic fixtures.

Unsupported formats should produce warnings, not partial writes.
