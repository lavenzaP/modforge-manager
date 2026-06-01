Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Python = if (Test-Path .\.venv\Scripts\python.exe) { ".\.venv\Scripts\python.exe" } else { "python" }

function Invoke-Checked {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$env:PYTHONPATH = "src"
Invoke-Checked "gui module import" {
    & $Python -c "import importlib; importlib.import_module('modforge.app'); importlib.import_module('modforge.gui.main_window'); print('GUI modules import')"
}
Invoke-Checked "tkinter gui runtime" {
    & $Python -c "from modforge.app import ModForgeApp, create_root; root = create_root(); root.withdraw(); app = ModForgeApp(root); print(app.root.title()); root.destroy()"
}
& $Python -m modforge.gui.main_window --check-dependency
if ($LASTEXITCODE -ne 0) {
  Write-Host "PySide6 optional GUI dependency is unavailable; tkinter runtime smoke passed."
  exit 0
}
