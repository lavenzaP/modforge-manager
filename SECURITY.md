# Security

ModForge writes to a game folder only during explicit apply.

Safety rules:

- Build a virtual plan before copying files.
- Restore or delete files from the latest ModForge manifest before reapply.
- Back up existing game files before overwriting them.
- Reject paths that escape the selected game folder.
- Keep unknown archive editing, encrypted PAK handling, and download automation out of scope.
