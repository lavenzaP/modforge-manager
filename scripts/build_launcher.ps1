Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Project = Join-Path $RepoRoot "desktop\ModForge.Launcher\ModForge.Launcher.csproj"
$Dist = Join-Path $RepoRoot "dist\ModForge.Launcher"

if (Test-Path $Dist) {
    Remove-Item -LiteralPath $Dist -Recurse -Force
}

dotnet publish $Project --configuration Release --runtime win-x64 --self-contained false --property:PublishDir="$Dist\"
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE"
}

Write-Host "Built $(Join-Path $Dist 'ModForge.Launcher.exe')"
