# Guided Safe Workflow V1

## Goal

Guided Safe Workflow V1 makes the first real user path explicit:

project -> scan -> plan -> conflict report -> apply staging -> apply game root
-> restore preview -> restore.

This milestone stays local and synthetic-fixture friendly. It does not add Nexus
downloads, encrypted archive support, arbitrary asset editing, installers, or
translation repacking.

Milestone 4 builds on this workflow with an MVP release-candidate support
contract for REFramework/nativePC, Unreal PAK/UCAS/UTOC, and Godot/Slay the
Spire 2 PCK mod families.

## Happy Path

1. Run `doctor` before creating a project. Missing project files are warnings,
   not hard failures.
2. Create a project with a game root, mods directory, staging directory, and
   built-in game profile.
3. Scan mods and show stable package order, enabled state, priority, package
   type, file count, and warnings.
4. Build a dry-run plan and show a compact risk summary.
5. Write a Markdown conflict report before any game-root write.
6. Apply to staging only after explicit confirmation.
7. Apply to the game root only after explicit confirmation, with backups and a
   game manifest.
8. Preview restore actions from the manifest before allowing restore.
9. Restore all files or selected manifest paths only after explicit
   confirmation.

## State Model

- `modforge.project.json`: project location, selected game profile, active user
  mod set, configured external tools.
- `.modforge/staging`: staging-only deployment output plus staging manifest.
- `.modforge/manifests`: game-root apply manifests.
- `.modforge/backups/<manifest-id>`: backups for overwritten game-root files.

Game manifests are the only manifests that can be restored. Staging manifests
remain inspectable records, not restore inputs.

## CLI Workflow

```powershell
$env:PYTHONPATH = "src"

$demo = Join-Path $env:TEMP ("modforge-safe-demo-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$game = Join-Path $demo "game"
$mods = Join-Path $demo "mods"
$project = Join-Path $demo "modforge.project.json"
$report = Join-Path $demo "conflict-report.md"

New-Item -ItemType Directory -Path $demo | Out-Null
Copy-Item -Recurse tests\fixtures\mhw_reframework_game $game
Copy-Item -Recurse tests\fixtures\mhw_reframework_mods $mods

python -m modforge doctor --project-file $project
python -m modforge project init --name "Wilds Demo" --game-root $game --mods-dir $mods --profile mhw-reframework --project-file $project
python -m modforge doctor --project-file $project
python -m modforge scan-mods --project-file $project
python -m modforge plan --project-file $project --summary
python -m modforge report --project-file $project --output $report

python -m modforge apply-staging --project-file $project
python -m modforge apply-staging --project-file $project --yes

python -m modforge apply-game --project-file $project
python -m modforge apply-game --project-file $project --yes

$manifest = Get-ChildItem (Join-Path $demo ".modforge\manifests") -Filter *.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --preview
python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --yes
```

## GUI Parity

The standard-library GUI follows the same core functions as the CLI. It scans
mods, renders plans, saves reports, confirms staging/game writes, previews
restore actions, blocks unsafe restore manifests, and restores selected or all
manifest paths.

## Safety Gates

- `apply-staging` refuses without `--yes`.
- `apply-game` refuses without `--yes`.
- `restore` refuses without `--yes`.
- `restore --preview` never writes files or updates `restored_at`.
- Restore blocks selected paths that do not exist in the manifest.
- Restore validates every destination path with the same safe destination check
  used for staging and game writes.
- Restore validates that backup files live under the manifest backup directory.
- Restore blocks missing backups before any file is changed.

## Acceptance Criteria

- `doctor` before project creation warns about the missing project file.
- `project init` creates a project JSON.
- `scan-mods` lists the synthetic Wilds/REFramework fixture mods.
- `plan --summary` reports operations, winning operations, skipped conflicts,
  conflicts, warnings, and risk.
- `report` names the conflicting `nativePC` destination and winner.
- `apply-staging` and `apply-game` refuse without `--yes`.
- `apply-staging --yes` writes only staging output.
- `apply-game --yes` writes a game manifest and backups for overwritten files.
- `restore --preview` reports actions without changing files or manifest state.
- `restore --yes` restores selected manifest paths.
