Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PreviousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
    Join-Path $RepoRoot "src"
}
else {
    "$(Join-Path $RepoRoot "src");$PreviousPythonPath"
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("modforge-winui-bridge-" + [System.Guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    $GameRoot = Join-Path $TempRoot "game"
    $ModsRoot = Join-Path $TempRoot "mods"
    $ProjectFile = Join-Path $TempRoot "modforge.project.json"
    $StagingRoot = Join-Path $TempRoot ".modforge\staging"
    $ConflictPath = Join-Path $GameRoot "nativePC\wp\swo\swo001\mod\swo001.mod3"

    Copy-Item -LiteralPath (Join-Path $RepoRoot "tests\fixtures\mhw_reframework_game") -Destination $GameRoot -Recurse
    Copy-Item -LiteralPath (Join-Path $RepoRoot "tests\fixtures\mhw_reframework_mods") -Destination $ModsRoot -Recurse
    New-Item -ItemType Directory -Path (Split-Path -Parent $ConflictPath) -Force | Out-Null
    "original sword model" | Set-Content -LiteralPath $ConflictPath -Encoding UTF8

    & python -m modforge project init --name "WinUI Bridge Smoke" --game-root $GameRoot --mods-dir $ModsRoot --staging-dir $StagingRoot --profile mhw-reframework --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "project init failed with exit code $LASTEXITCODE"
    }

    $Project = & python -m modforge project show --project-file $ProjectFile --json | ConvertFrom-Json
    if ($Project.name -ne "WinUI Bridge Smoke") {
        throw "project show returned unexpected project name: $($Project.name)"
    }
    if ($Project.game_profile.id -ne "mhw-reframework") {
        throw "project show returned unexpected profile: $($Project.game_profile.id)"
    }

    $Mods = & python -m modforge scan-mods --project-file $ProjectFile --json | ConvertFrom-Json
    if ($Mods.Count -lt 1) {
        throw "scan-mods returned no mods"
    }

    & python -m modforge profile disable nativeswordpatch --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "profile disable failed with exit code $LASTEXITCODE"
    }
    $DisabledScan = & python -m modforge scan-mods --project-file $ProjectFile --json | ConvertFrom-Json
    $DisabledPatch = $DisabledScan | Where-Object { $_.id -eq "nativeswordpatch" } | Select-Object -First 1
    if ($null -eq $DisabledPatch) {
        throw "disable smoke could not find nativeswordpatch"
    }
    if ($DisabledPatch.enabled -ne $false) {
        throw "disable smoke expected nativeswordpatch to be disabled"
    }

    & python -m modforge profile enable nativeswordpatch --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "profile enable failed with exit code $LASTEXITCODE"
    }
    $EnabledScan = & python -m modforge scan-mods --project-file $ProjectFile --json | ConvertFrom-Json
    $EnabledPatch = $EnabledScan | Where-Object { $_.id -eq "nativeswordpatch" } | Select-Object -First 1
    if ($null -eq $EnabledPatch) {
        throw "enable smoke could not find nativeswordpatch"
    }
    if ($EnabledPatch.enabled -ne $true) {
        throw "enable smoke expected nativeswordpatch to be enabled"
    }

    $Plan = & python -m modforge plan --project-file $ProjectFile --json | ConvertFrom-Json
    if (-not $Plan.dry_run) {
        throw "plan is not marked dry-run"
    }
    if ($Plan.operations.Count -lt 1) {
        throw "plan returned no operations"
    }

    & python -m modforge profile set-priority --project-file $ProjectFile nativeswordpatch nativesword | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "profile set-priority failed with exit code $LASTEXITCODE"
    }
    $Replanned = & python -m modforge plan --project-file $ProjectFile --json | ConvertFrom-Json
    $SwordConflict = $Replanned.conflicts | Where-Object { $_.destination_path -eq "nativePC/wp/swo/swo001/mod/swo001.mod3" } | Select-Object -First 1
    if (-not $SwordConflict) {
        throw "priority smoke could not find the sword conflict"
    }
    if ($SwordConflict.winning_mod -ne "NativeSword") {
        throw "priority smoke expected NativeSword to win, got $($SwordConflict.winning_mod)"
    }

    $Manifest = & python -m modforge apply-staging --project-file $ProjectFile --yes --json | ConvertFrom-Json
    if ($Manifest.target -ne "staging") {
        throw "apply-staging returned unexpected target: $($Manifest.target)"
    }
    if (-not (Test-Path (Join-Path $StagingRoot ".modforge-install-manifest.json"))) {
        throw "staging manifest was not created"
    }
    if ((Get-Content -LiteralPath $ConflictPath -Raw).Trim() -ne "original sword model") {
        throw "apply-staging changed the game folder"
    }

    Write-Host "WinUI real bridge smoke passed: project show, scan, enable/disable, plan, priority reorder, and staging contract are usable."
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
    if (Test-Path $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
