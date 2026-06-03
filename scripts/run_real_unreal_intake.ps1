param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [string]$Profile = "stellar-blade.experimental",

    [string]$Output,

    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$previousPythonPath = $env:PYTHONPATH

function ConvertTo-SafeFilePart {
    param([string]$Value)
    $safe = ($Value -replace '[^A-Za-z0-9._-]+', '-').Trim("-")
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return "mod-package"
    }
    return $safe
}

function Resolve-OutputPath {
    param(
        [string]$RawOutput,
        [System.IO.FileSystemInfo]$SourceItem
    )
    if (-not [string]::IsNullOrWhiteSpace($RawOutput)) {
        if ([System.IO.Path]::IsPathRooted($RawOutput)) {
            return [System.IO.Path]::GetFullPath($RawOutput)
        }
        return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $RawOutput))
    }

    $documents = [Environment]::GetFolderPath("MyDocuments")
    if ([string]::IsNullOrWhiteSpace($documents)) {
        $documents = $repo
    }
    $reportRoot = Join-Path $documents "ModForge Manager\Reports"
    $sourceName = if ($SourceItem.PSIsContainer) {
        $SourceItem.Name
    }
    else {
        [System.IO.Path]::GetFileNameWithoutExtension($SourceItem.Name)
    }
    $safeSource = ConvertTo-SafeFilePart $sourceName
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $nonce = [guid]::NewGuid().ToString("N").Substring(0, 8)
    return Join-Path $reportRoot "unreal-intake-$safeSource-$timestamp-$nonce.json"
}

try {
    $sourcePath = (Resolve-Path -LiteralPath $Source -ErrorAction Stop).ProviderPath
    $sourceItem = Get-Item -LiteralPath $sourcePath
    $outputPath = Resolve-OutputPath -RawOutput $Output -SourceItem $sourceItem

    $env:PYTHONPATH = Join-Path $repo "src"
    $rawJson = & $Python -m modforge unreal intake `
        --profile $Profile `
        --source $sourceItem.FullName `
        --output $outputPath `
        --json
    $exitCode = $LASTEXITCODE
    $jsonText = ($rawJson -join "`n")

    try {
        $report = $jsonText | ConvertFrom-Json
    }
    catch {
        if (-not [string]::IsNullOrWhiteSpace($jsonText)) {
            Write-Host $jsonText
        }
        throw "Unreal intake did not return parseable JSON."
    }

    Write-Host "Unreal intake report (read-only)"
    Write-Host "Source: $($sourceItem.FullName)"
    Write-Host "Report: $outputPath"
    Write-Host "Profile: $($report.profile_id)"
    Write-Host "Package shape: $($report.package_shape)"
    $ignoredFiles = @($report.operations_preview | Where-Object { $_.action -eq "ignored" }).Count
    $managedFiles = @($report.operations_preview | Where-Object {
        $_.action -ne "unmanaged" -and $_.action -ne "ignored"
    }).Count
    Write-Host ("Files: {0}" -f $report.summary.files)
    Write-Host ("Managed files: {0}" -f $managedFiles)
    Write-Host ("Ignored files: {0}" -f $ignoredFiles)
    Write-Host ("Sidecar groups: {0}" -f $report.summary.sidecar_groups)
    Write-Host ("High-risk files: {0}" -f $report.summary.high_risk_files)
    Write-Host ("Unmanaged files: {0}" -f $report.summary.unmanaged_files)
    Write-Host ("Warnings: {0}" -f @($report.warnings).Count)
    Write-Host ("Blocked items: {0}" -f @($report.blocked).Count)

    if (@($report.warnings).Count -gt 0) {
        Write-Host ""
        Write-Host "Warnings:"
        @($report.warnings) | Select-Object -First 5 | ForEach-Object {
            Write-Host "- $_"
        }
    }
    if (@($report.blocked).Count -gt 0) {
        Write-Host ""
        Write-Host "Blocked:"
        @($report.blocked) | Select-Object -First 5 | ForEach-Object {
            Write-Host "- $_"
        }
    }

    if ($exitCode -ne 0) {
        throw "Intake finished with exit code $exitCode. Review the saved report before continuing."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
