# MVP RC Certification

## Goal

Milestone 4 turned ModForge Manager into an MVP release candidate: a local,
Windows-first mod manager that can safely scan, plan, apply, inspect, and restore
supported mod workflows through synthetic fixtures and repeatable smoke checks.
Milestone 5 freezes large feature work and focuses on release readiness.

## Certified Core Mod Families

The MVP release candidate treats these three families as the required support
baseline:

- REFramework/nativePC mods, including Monster Hunter Wilds style layouts.
- Unreal `~mods` archive mods, including `.pak`, `.ucas`, and `.utoc` files.
- Godot/Slay the Spire 2 mods-folder workflows, including `.pck` files.

For this milestone, "perfect support" means each certified family has a tested
local workflow for scan, plan, conflict report, staging apply, game apply,
manifest inspection, restore preview, restore, doctor/audit checks, and docs.

## Explicit Exclusions

These are intentionally outside the MVP RC scope:

- Nexus Mods login, API, or downloads.
- Encrypted PAK support.
- Arbitrary `.uasset` editing.
- Godot PCK or Unreal archive repacking.
- Virtual filesystem behavior.
- Full MO2/Vortex replacement behavior.
- Installer generation, signing, auto-update, or public release publishing.
- Full translation repacking.

## Release Gates

- `python -m unittest discover -s tests`
- `python -m compileall -q src tests`
- `python -m modforge doctor --project-file modforge.project.json`
- `python -m modforge plan --project-file modforge.project.json --summary --json`
- PowerShell smoke scripts under `scripts/`
- Optional lint gate through `scripts/lint.ps1`

## Acceptance Criteria

- Manifest list/show/latest work from the CLI.
- Restore preview is non-mutating.
- Restore stays manifest-bound and blocks unsafe manifests.
- Project export/import/audit works without copying game files, mod archives, or
  backup binaries by default.
- Doctor exposes project audit warnings and errors.
- The tkinter GUI exposes project health and manifest/restore state.
- REFramework, Unreal, and Godot/STS2 family fixtures pass end-to-end tests.
- README and docs describe supported scope and limitations.
- Release checklist, support matrix, MVP status, and changelog are present.
