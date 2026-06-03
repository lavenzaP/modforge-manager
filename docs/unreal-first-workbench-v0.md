# Unreal-First Workbench v0

ModForge is pivoting from broad equal-priority game support to an Unreal-first
workbench. The goal is to make one practical workflow feel real before adding
more games.

## Primary Shape

- Primary profile: `unreal-pak`
- Representative experimental profile: `stellar-blade.experimental`
- First safe write target: project staging directory
- WinUI game-folder apply: locked
- Translation surface: read-only localization inventory from staged output
- Real-mod readiness gate: read-only Unreal intake report before any install
  test with actual mod packages

## What v0 Supports

- Scan loose folders, ZIPs, and Unreal archive files.
- Plan Unreal `.pak/.ucas/.utoc` archive deployment to `Content/Paks/~mods`.
- Preserve extracted or loose content paths when a package already contains a
  valid Unreal-style layout.
- Detect destination conflicts and let the user adjust priority before staging.
- Apply the reviewed winning plan to staging only.
- Inspect staged records and run localization inventory from WinUI.
- Classify JSON/CSV/TXT as extractable, `.locres/.locmeta` as tool-required,
  `.pak/.ucas/.utoc` as staged archives, and `.uasset/.uexp/.ubulk` as binary
  assets.
- Run `unreal intake` against a folder, ZIP, or single package file to preview
  Stellar Blade/CNS style mappings, sidecar groups, runtime-file risk, LogicMods
  candidates, and unmanaged files without writing anything.

## What v0 Does Not Support

- Encrypted PAK extraction.
- PAK/UCAS/UTOC repacking.
- `.uasset` editing.
- Automatic translation service calls.
- Nexus downloads.
- WinUI game-folder writes.
- Installer packaging.

## Before Real Mod Testing

Use synthetic fixtures first:

```powershell
python -m modforge unreal intake --profile stellar-blade.experimental --source <mod-folder-or-zip> --json
```

Real mod testing should start only after the intake report can classify the
package tree, preview destinations, flag high-risk runtime files, and leave
unknown files unmanaged. The first real-mod pass should capture the package tree
and review the intake report, not install into the game folder.

## Regression Families

REFramework/nativePC and Godot/STS2 remain in tests so the core scan/plan/apply
machinery does not regress. They are not the first product surface for new
workflow UX.
