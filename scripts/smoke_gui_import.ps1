Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
python -c "import importlib; importlib.import_module('modforge.app'); importlib.import_module('modforge.gui.main_window'); print('GUI modules import')"
python -m modforge.gui.main_window --check-dependency
if ($LASTEXITCODE -ne 0) {
  Write-Host "PySide6 optional GUI dependency is unavailable; tkinter import smoke passed."
  exit 0
}
