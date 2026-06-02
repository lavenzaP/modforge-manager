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

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("modforge-public-staging-" + [System.Guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    $GameRoot = Join-Path $TempRoot "game"
    $ModsRoot = Join-Path $TempRoot "mods"
    $ProjectFile = Join-Path $TempRoot "modforge.project.json"
    $StagingRoot = Join-Path $TempRoot ".modforge\staging"
    $GameProbe = Join-Path $GameRoot "nativePC\wp\swo\swo001\mod\swo001.mod3"

    Copy-Item -LiteralPath (Join-Path $RepoRoot "tests\fixtures\mhw_reframework_game") -Destination $GameRoot -Recurse
    Copy-Item -LiteralPath (Join-Path $RepoRoot "tests\fixtures\mhw_reframework_mods") -Destination $ModsRoot -Recurse

    New-Item -ItemType Directory -Path (Split-Path -Parent $GameProbe) -Force | Out-Null
    "original game file" | Set-Content -LiteralPath $GameProbe -Encoding UTF8
    $OriginalGameProbe = Get-Content -LiteralPath $GameProbe -Raw

    & python -m modforge project init --name "Public Staging Smoke" --game-root $GameRoot --mods-dir $ModsRoot --staging-dir $StagingRoot --profile mhw-reframework --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "project init failed with exit code $LASTEXITCODE"
    }

    $ScannedMods = & python -m modforge scan-mods --project-file $ProjectFile --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "scan-mods failed with exit code $LASTEXITCODE"
    }
    if ($ScannedMods.Count -lt 1) {
        throw "scan-mods returned no mods"
    }

    $Plan = & python -m modforge plan --project-file $ProjectFile --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "plan failed with exit code $LASTEXITCODE"
    }
    if (-not $Plan.dry_run) {
        throw "plan was not marked dry-run"
    }
    if ($Plan.operations.Count -lt 1) {
        throw "plan returned no operations"
    }

    $Manifest = & python -m modforge apply-staging --project-file $ProjectFile --yes --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "apply-staging failed with exit code $LASTEXITCODE"
    }
    if ($Manifest.target -ne "staging") {
        throw "apply-staging returned unexpected target: $($Manifest.target)"
    }
    if ($Manifest.records.Count -lt 1) {
        throw "staging manifest returned no records"
    }

    $ManifestPath = Join-Path $StagingRoot ".modforge-install-manifest.json"
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        throw "staging install manifest was not created"
    }

    $StagedFiles = Get-ChildItem -LiteralPath $StagingRoot -Recurse -File |
        Where-Object { $_.Name -ne ".modforge-install-manifest.json" }
    if ($StagedFiles.Count -lt 1) {
        throw "staging directory contains no deployed files"
    }

    $AfterGameProbe = Get-Content -LiteralPath $GameProbe -Raw
    if ($AfterGameProbe -ne $OriginalGameProbe) {
        throw "apply-staging changed the game folder"
    }

    Write-Host "Public staging smoke passed: scan, dry-run plan, apply-staging, staging manifest, and no game-folder write."
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}

