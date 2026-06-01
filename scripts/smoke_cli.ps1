Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Python = if (Test-Path .\.venv\Scripts\python.exe) { ".\.venv\Scripts\python.exe" } else { "python" }

function Invoke-Checked {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$env:PYTHONPATH = "src"
Invoke-Checked "version" { & $Python -m modforge --version }
Invoke-Checked "profiles" { & $Python -m modforge profiles --json }

$demo = Join-Path $env:TEMP ("modforge-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$game = Join-Path $demo "game"
$mods = Join-Path $demo "mods"
$project = Join-Path $demo "modforge.project.json"

New-Item -ItemType Directory -Path $demo | Out-Null
Copy-Item -Recurse tests\fixtures\fake_game $game
Copy-Item -Recurse tests\fixtures\fake_mods $mods

Invoke-Checked "doctor before init" { & $Python -m modforge doctor --project-file $project }
Invoke-Checked "project init" {
    & $Python -m modforge project init --name Smoke --game-root $game --mods-dir $mods --project-file $project
}
Invoke-Checked "doctor after init" { & $Python -m modforge doctor --project-file $project }
Invoke-Checked "plan" { & $Python -m modforge plan --project-file $project --summary --json }
Invoke-Checked "apply-staging" { & $Python -m modforge apply-staging --project-file $project --yes }
