Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
python -m modforge --version
python -m modforge profiles --json

$demo = Join-Path $env:TEMP ("modforge-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$game = Join-Path $demo "game"
$mods = Join-Path $demo "mods"
$project = Join-Path $demo "modforge.project.json"

New-Item -ItemType Directory -Path $demo | Out-Null
Copy-Item -Recurse tests\fixtures\fake_game $game
Copy-Item -Recurse tests\fixtures\fake_mods $mods

python -m modforge doctor --project-file $project
python -m modforge project init --name Smoke --game-root $game --mods-dir $mods --project-file $project
python -m modforge doctor --project-file $project
python -m modforge plan --project-file $project --summary --json
python -m modforge apply-staging --project-file $project --yes
