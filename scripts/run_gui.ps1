param(
    [switch]$Check
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $VenvPython) {
    $Python = (Resolve-Path $VenvPython).Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = (Get-Command python).Source
} elseif (Test-Path $BundledPython) {
    $Python = (Resolve-Path $BundledPython).Path
} else {
    throw "No usable Python executable found. Install Python 3.12+ or run scripts\dev_setup.ps1 first."
}

$env:PYTHONPATH = Join-Path $RepoRoot "src"

Push-Location $RepoRoot
try {
    if ($Check) {
        & $Python -c "from modforge.app import ModForgeApp, create_root; root = create_root(); root.withdraw(); app = ModForgeApp(root); print(app.root.title()); root.destroy()"
    } else {
        & $Python -m modforge.app @args
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
