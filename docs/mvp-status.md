# MVP Status

Status: MVP core complete, staging-first public preview hardening in progress.

Baseline commit before freeze hardening: `fe222bd`.

## Freeze Scope

The MVP is now feature-frozen for large additions. Remaining work should be
limited to release readiness:

- Safety edge tests.
- Support matrix documentation.
- Changelog and release checklist.
- Windows smoke script reliability.
- Optional lint setup cleanup.
- Public safety documentation and repository content audit.
- Staging-first README wording in separate English and Korean README files.

## Release Blockers

- Required test gate must pass.
- Release smoke must stop on native command failures.
- Certified core mod family support must remain covered by tests.
- No real game files or real mod archives may be committed.
- Real staging must pass from the CLI/core and WinUI bridge before public
  visibility.
- WinUI game apply may remain locked in the public preview as an explicit safety
  boundary.

## Deferred After MVP RC

- Nexus Mods integration.
- Encrypted archive handling.
- Asset editing and archive repacking.
- Installer/signing/update flow.
- Virtual filesystem behavior.
- WinUI game apply/restore destructive-action exposure.
