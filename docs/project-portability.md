# Project Portability

Project portability is metadata-only by default.

## Commands

```powershell
python -m modforge project audit --project-file modforge.project.json
python -m modforge project audit --project-file modforge.project.json --json
python -m modforge project export --project-file modforge.project.json --out .modforge\project-export.json
python -m modforge project import .modforge\project-export.json --target .\imported-project
```

## Export Contract

Included:

- Project configuration.
- Game profile.
- User mod-set profiles, enabled state, and priority order.
- External tool configuration strings.
- Manifest metadata, when not disabled.

Excluded by default:

- Game files.
- Mod archives or loose mod payloads.
- Backup binaries.
- External tool executables.
- Crash dumps and logs.

Imported projects use a fresh staging directory under the target folder. Existing
absolute game and mod paths are preserved so `doctor` and `project audit` can
report what needs remapping.
