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
Invoke-Checked "unittest" { & $Python -m unittest discover -s tests }
Invoke-Checked "compileall" { & $Python -m compileall -q src tests }
