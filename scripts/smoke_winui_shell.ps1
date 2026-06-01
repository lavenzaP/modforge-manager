Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "build_winui_shell.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "build_winui_shell failed with exit code $LASTEXITCODE"
}

$ExePath = Get-ChildItem -Path (Join-Path $RepoRoot "dist\ModForge.WinUI") -Filter *.exe -File -Recurse | Select-Object -First 1 -ExpandProperty FullName
if (-not $ExePath) {
    throw "WinUI executable was not found."
}

$Process = Start-Process -FilePath $ExePath -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 2
    if ($Process.HasExited) {
        throw "WinUI shell exited early with code $($Process.ExitCode)."
    }
}
finally {
    if (-not $Process.HasExited) {
        $Process.CloseMainWindow() | Out-Null
        Start-Sleep -Milliseconds 500
        if (-not $Process.HasExited) {
            $Process.Kill()
        }
    }
}

Write-Host "WinUI shell smoke passed: $ExePath"
