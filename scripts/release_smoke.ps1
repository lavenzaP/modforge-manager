Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

.\scripts\run_tests.ps1
.\scripts\smoke_cli.ps1
.\scripts\smoke_gui_import.ps1
