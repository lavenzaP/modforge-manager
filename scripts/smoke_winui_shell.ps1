Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

$BridgeCommands = Get-Content -LiteralPath (Join-Path $RepoRoot "desktop\ModForge.WinUI\PythonCoreService.cs") -Raw
if ($BridgeCommands -match '"apply-game"' -or $BridgeCommands -match '"restore"') {
    throw "WinUI Python bridge wires a destructive game apply or restore command."
}

$MainWindowCommands = Get-Content -LiteralPath (Join-Path $RepoRoot "desktop\ModForge.WinUI\MainWindow.xaml.cs") -Raw
if ($MainWindowCommands -match 'pythonCore\.(ApplyGame|Restore)') {
    throw "WinUI MainWindow calls a destructive game apply or restore bridge method."
}

& (Join-Path $PSScriptRoot "build_winui_shell.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "build_winui_shell failed with exit code $LASTEXITCODE"
}

$ExePath = Get-ChildItem -Path (Join-Path $RepoRoot "dist\ModForge.WinUI") -Filter *.exe -File -Recurse | Select-Object -First 1 -ExpandProperty FullName
if (-not $ExePath) {
    throw "WinUI executable was not found."
}

$BeforePythonIds = @(Get-Process -Name python, python3, py -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })

$Process = Start-Process -FilePath $ExePath -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 2
    if ($Process.HasExited) {
        throw "WinUI shell exited early with code $($Process.ExitCode)."
    }
    $AfterPython = @(
        Get-Process -Name python, python3, py -ErrorAction SilentlyContinue |
            Where-Object { $BeforePythonIds -notcontains $_.Id }
    )
    if ($AfterPython.Count -gt 0) {
        $ids = ($AfterPython | ForEach-Object { $_.Id }) -join ", "
        throw "WinUI startup launched a Python process unexpectedly. New process ids: $ids"
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

Write-Host "WinUI shell smoke passed: no destructive bridge command is wired, startup did not launch ModForge Python, and executable stayed open: $ExePath"
