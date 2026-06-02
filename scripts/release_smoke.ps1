param(
    [switch]$IncludeLint,
    [switch]$IncludeDesktop,
    [switch]$IncludeWinUI
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

.\scripts\public_staging_smoke.ps1
if ($LASTEXITCODE -ne 0) {
    throw "public_staging_smoke failed with exit code $LASTEXITCODE"
}

if ($IncludeDesktop) {
    .\scripts\build_windows_shell.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "build_windows_shell failed with exit code $LASTEXITCODE"
    }
    .\scripts\smoke_windows_shell.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_windows_shell failed with exit code $LASTEXITCODE"
    }
}

if ($IncludeWinUI) {
    .\scripts\smoke_winui_shell.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_winui_shell failed with exit code $LASTEXITCODE"
    }
    .\scripts\smoke_winui_bridge_real.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_winui_bridge_real failed with exit code $LASTEXITCODE"
    }
}
