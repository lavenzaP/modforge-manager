Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "build_launcher.ps1")

$Exe = Join-Path $RepoRoot "dist\ModForge.Launcher\ModForge.Launcher.exe"
if (-not (Test-Path $Exe)) {
    throw "Launcher exe was not produced: $Exe"
}

$SelfTest = Start-Process -FilePath $Exe -ArgumentList "--self-test" -PassThru -Wait
if ($SelfTest.ExitCode -ne 0) {
    throw "Launcher self-test failed with exit code $($SelfTest.ExitCode)"
}

$SmokeOut = Join-Path $RepoRoot "dist\ModForge.Launcher\smoke.json"
if (Test-Path $SmokeOut) {
    Remove-Item -LiteralPath $SmokeOut -Force
}

$SmokeRoot = Join-Path $RepoRoot "dist\ModForge.Launcher\smoke-work"
if (Test-Path $SmokeRoot) {
    Remove-Item -LiteralPath $SmokeRoot -Recurse -Force
}

$SmokeMods = Join-Path $SmokeRoot "Mods"
$SmokeGame = Join-Path $SmokeRoot "Game"
New-Item -ItemType Directory -Force -Path (Join-Path $SmokeMods "Alpha") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SmokeMods "Beta") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SmokeGame "SmokeGame\Content\Paks") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SmokeGame "SmokeGame\Binaries\Win64") | Out-Null
Set-Content -LiteralPath (Join-Path $SmokeGame "SmokeGame\Binaries\Win64\SmokeGame-Win64-Shipping.exe") -Value ""
Set-Content -LiteralPath (Join-Path $SmokeMods "Alpha\alpha.pak") -Value "alpha"
Set-Content -LiteralPath (Join-Path $SmokeMods "Beta\beta.pak") -Value "beta"
Set-Content -LiteralPath (Join-Path $SmokeMods "modforge-state.json") -Value '{"Mods":[{"Name":"Beta","Enabled":true,"Priority":1},{"Name":"Alpha","Enabled":false,"Priority":2}]}'

$Arguments = '--smoke --mods "' + $SmokeMods + '" --game "' + $SmokeGame + '" --out "' + $SmokeOut + '"'
$Process = Start-Process -FilePath $Exe -ArgumentList $Arguments -PassThru -Wait
if ($Process.ExitCode -ne 0) {
    throw "Launcher smoke failed with exit code $($Process.ExitCode)"
}
if (-not (Test-Path $SmokeOut)) {
    throw "Launcher smoke did not write JSON summary: $SmokeOut"
}

$Output = Get-Content -LiteralPath $SmokeOut -Raw
if ($Output -notmatch "modCount") {
    throw "Launcher smoke JSON is invalid: $Output"
}
if ($Output -notmatch '"modCount":2' -or $Output -notmatch '"enabledCount":1') {
    throw "Launcher smoke did not use the standalone ModForge state: $Output"
}

Write-Host "Launcher smoke passed: $Output"
