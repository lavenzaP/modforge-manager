param(
    [switch]$IncludeLint
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

.\scripts\run_tests.ps1
if ($LASTEXITCODE -ne 0) {
    throw "run_tests failed with exit code $LASTEXITCODE"
}

if ($IncludeLint) {
    .\scripts\lint.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "lint failed with exit code $LASTEXITCODE"
    }
}

.\scripts\smoke_cli.ps1
if ($LASTEXITCODE -ne 0) {
    throw "smoke_cli failed with exit code $LASTEXITCODE"
}

.\scripts\smoke_gui_import.ps1
if ($LASTEXITCODE -ne 0) {
    throw "smoke_gui_import failed with exit code $LASTEXITCODE"
}
