Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PreviousPythonPath = $env:PYTHONPATH
$Python = if (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
    Join-Path $RepoRoot ".venv\Scripts\python.exe"
}
else {
    "python"
}
$env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
    Join-Path $RepoRoot "src"
}
else {
    "$(Join-Path $RepoRoot "src");$PreviousPythonPath"
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("modforge-unreal-workbench-" + [System.Guid]::NewGuid().ToString("N"))

try {
    $GameRoot = Join-Path $TempRoot "game"
    $ModsRoot = Join-Path $TempRoot "mods"
    $ProjectFile = Join-Path $TempRoot "modforge.project.json"
    $StagingRoot = Join-Path $TempRoot ".modforge\staging"
    $ModRoot = Join-Path $ModsRoot "TextPak"

    New-Item -ItemType Directory -Path (Join-Path $ModRoot "Content\Localization\Game\en") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ModRoot "Content\Data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ModRoot "Content\Art") -Force | Out-Null
    New-Item -ItemType Directory -Path $GameRoot -Force | Out-Null
    [System.IO.File]::WriteAllBytes((Join-Path $ModRoot "CoolOutfit_P.pak"), [byte[]](112, 97, 107))
    [System.IO.File]::WriteAllBytes((Join-Path $ModRoot "Content\Localization\Game\en\Game.locres"), [byte[]](108, 111, 99))
    [System.IO.File]::WriteAllText((Join-Path $ModRoot "Content\Data\menu.json"), '{"start": "Start"}')
    [System.IO.File]::WriteAllBytes((Join-Path $ModRoot "Content\Art\Icon.uasset"), [byte[]](117, 97))

    & $Python -m modforge project init --name "Unreal Workbench Smoke" --game-root $GameRoot --mods-dir $ModsRoot --staging-dir $StagingRoot --profile unreal-pak --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "project init failed with exit code $LASTEXITCODE"
    }

    & $Python -m modforge apply-staging --project-file $ProjectFile --yes | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "apply-staging failed with exit code $LASTEXITCODE"
    }

    $Inventory = & $Python -m modforge translation inventory --project-file $ProjectFile --target staging --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "translation inventory failed with exit code $LASTEXITCODE"
    }
    if ($Inventory.profile_id -ne "unreal-pak") {
        throw "unexpected profile id: $($Inventory.profile_id)"
    }
    if ($Inventory.summary.extractable -lt 1) {
        throw "inventory did not detect extractable JSON/CSV/TXT files"
    }
    if ($Inventory.summary.tool_required -lt 1) {
        throw "inventory did not detect Unreal localization resources"
    }
    if ($Inventory.summary.archive_not_inspected -lt 1) {
        throw "inventory did not detect staged Unreal archives"
    }
    if ($Inventory.summary.binary_asset -lt 1) {
        throw "inventory did not detect binary Unreal assets"
    }

    Write-Host "Unreal workbench smoke passed: staging and localization inventory are consistent."
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
