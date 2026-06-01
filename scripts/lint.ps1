Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Python = if (Test-Path .\.venv\Scripts\python.exe) { ".\.venv\Scripts\python.exe" } else { "python" }

& $Python -m ruff --version
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Ruff is not installed. Run: .\.venv\Scripts\python.exe -m pip install -e ".[dev]"'
    exit 1
}

& $Python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python -m ruff format --check .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
