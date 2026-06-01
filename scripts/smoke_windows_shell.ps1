Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoRoot "dist\ModForge.App\ModForge.App.exe"

& (Join-Path $PSScriptRoot "build_windows_shell.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "build_windows_shell failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $ExePath)) {
    throw "Windows shell exe was not produced: $ExePath"
}

$Process = Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -PassThru
Start-Sleep -Seconds 2

if ($Process.HasExited) {
    throw "Windows shell exited during smoke check with code $($Process.ExitCode)"
}

$closed = $Process.CloseMainWindow()
if (-not $closed) {
    Stop-Process -Id $Process.Id -Force
}

Write-Host "Windows shell smoke passed: $ExePath"
