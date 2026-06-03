$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $repo "src"
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("modforge-unreal-intake-" + [guid]::NewGuid().ToString("N"))
$source = Join-Path $temp "mixed"
$reportPath = Join-Path $temp "reports\intake.json"
$helperReportPath = Join-Path $temp "reports\helper-intake.json"
New-Item -ItemType Directory -Path $source | Out-Null

function Write-Stub {
    param([string]$RelativePath, [string]$Text = "stub")
    $path = Join-Path $source $RelativePath
    $parent = Split-Path -Parent $path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($path, $Text)
}

try {
    Write-Stub "CoolMod_P.pak"
    Write-Stub "CoolMod_P.ucas"
    Write-Stub "CoolMod_P.utoc"
    Write-Stub "CoolMod_P.json" "{}"
    Write-Stub "SB\Binaries\Win64\ue4ss\Mods\CNS\main.lua" "print('ok')"
    Write-Stub "dwmapi.dll"
    Write-Stub "LogicMods\Experimental\foo.uasset"
    Write-Stub "unknown.bin"

    $json = python -m modforge unreal intake --profile stellar-blade.experimental --source $source --output $reportPath --json
    $report = $json | ConvertFrom-Json

    if (-not $report.ok) {
        throw "Expected intake report to be ok."
    }
    if ($report.package_shape -ne "mixed_unreal_package") {
        throw "Expected mixed_unreal_package, got $($report.package_shape)."
    }
    if ($report.summary.sidecar_groups -lt 1) {
        throw "Expected at least one sidecar group."
    }
    if ($report.summary.high_risk_files -lt 2) {
        throw "Expected runtime files to be high-risk."
    }
    if ($report.summary.unmanaged_files -ne 1) {
        throw "Expected exactly one unmanaged file."
    }
    if (-not ($report.warnings -match "LogicMods layout is experimental")) {
        throw "Expected LogicMods experimental warning."
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        throw "Expected intake report file to be written."
    }
    $saved = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    if ($saved.summary.files -ne $report.summary.files) {
        throw "Saved intake report does not match stdout summary."
    }

    $before = Get-ChildItem -Path $source -Recurse -File | ForEach-Object { $_.FullName } | Sort-Object
    $null = python -m modforge unreal intake --profile stellar-blade.experimental --source $source --json
    $after = Get-ChildItem -Path $source -Recurse -File | ForEach-Object { $_.FullName } | Sort-Object
    if (@($before).Count -ne @($after).Count) {
        throw "Intake report changed file count."
    }

    & (Join-Path $repo "scripts\run_real_unreal_intake.ps1") -Source $source -Output $helperReportPath | Out-Host
    if (-not (Test-Path -LiteralPath $helperReportPath)) {
        throw "Expected helper intake report file to be written."
    }
    $helperSaved = Get-Content -LiteralPath $helperReportPath -Raw | ConvertFrom-Json
    if ($helperSaved.profile_id -ne "stellar-blade.experimental") {
        throw "Helper intake report used unexpected profile: $($helperSaved.profile_id)"
    }
    $afterHelper = Get-ChildItem -Path $source -Recurse -File | ForEach-Object { $_.FullName } | Sort-Object
    if (@($before).Count -ne @($afterHelper).Count) {
        throw "Real intake helper changed file count."
    }

    Write-Host "Unreal intake smoke passed: synthetic Stellar Blade/CNS package classified read-only."
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
