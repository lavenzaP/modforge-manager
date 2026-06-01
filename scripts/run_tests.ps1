Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m compileall -q src tests
