Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoRoot "dist\ModForge.App\ModForge.App.exe"

$ShellSource = Get-ChildItem -Path (Join-Path $RepoRoot "desktop\ModForge.App") -Filter *.cs -File |
    ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw } |
    Out-String
if ($ShellSource -match "Preview restore" -or $ShellSource -match "Restore selected files" -or $ShellSource -match "Restore all from latest") {
    throw "WPF fallback still labels staging-first actions as restore actions."
}
if ($ShellSource -match "Confirm game apply" -or $ShellSource -match "AdvanceState\(WorkflowState\.RestoreAvailable") {
    throw "WPF fallback still exposes or advances a mock game-apply confirmation path."
}
if ($ShellSource -match "Requires confirmation and creates backups plus a restore manifest") {
    throw "WPF fallback still advertises game apply confirmation in sample setup data."
}
if ($ShellSource -notmatch "Preview staged records" -or $ShellSource -notmatch "Game writes locked") {
    throw "WPF fallback is missing the staging-first locked-write action labels."
}

& (Join-Path $PSScriptRoot "build_windows_shell.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "build_windows_shell failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $ExePath)) {
    throw "Windows shell exe was not produced: $ExePath"
}

$Process = Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

if ($Process.HasExited) {
    throw "Windows shell exited during smoke check with code $($Process.ExitCode)"
}

$closed = $Process.CloseMainWindow()
if (-not $closed) {
    Stop-Process -Id $Process.Id -Force
}

Write-Host "Windows shell smoke passed: $ExePath"
