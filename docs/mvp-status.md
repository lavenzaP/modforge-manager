# MVP Status

Status: MVP core complete, release-candidate freeze in progress.

Baseline commit before freeze hardening: `fe222bd`.

## Freeze Scope

The MVP is now feature-frozen for large additions. Remaining work should be
limited to release readiness:

- Safety edge tests.
- Support matrix documentation.
- Changelog and release checklist.
- Windows smoke script reliability.
- Optional lint setup cleanup.

## Release Blockers

- Required test gate must pass.
- Release smoke must stop on native command failures.
- Certified core mod family support must remain covered by tests.
- No real game files or real mod archives may be committed.

## Deferred After MVP RC

- Nexus Mods integration.
- Encrypted archive handling.
- Asset editing and archive repacking.
- Installer/signing/update flow.
- Virtual filesystem behavior.
