param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Join-Path $RepoRoot "desktop\ModForge.WinUI"
$ProjectPath = Join-Path $ProjectRoot "ModForge.WinUI.csproj"
$DistRoot = Join-Path $RepoRoot "dist\ModForge.WinUI"
$DotnetHome = Join-Path $RepoRoot ".dotnet_cli_home"
$NuGetPackages = Join-Path $RepoRoot ".nuget\packages"
$NuGetConfig = Join-Path $RepoRoot "build\winui-nuget.config"

New-Item -ItemType Directory -Path $DotnetHome, $NuGetPackages, (Split-Path -Parent $NuGetConfig) -Force | Out-Null
$env:DOTNET_CLI_HOME = $DotnetHome
$env:NUGET_PACKAGES = $NuGetPackages
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"

if (-not (Test-Path $NuGetConfig)) {
    @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
"@ | Set-Content -LiteralPath $NuGetConfig -Encoding UTF8
}

if (-not (Test-Path $ProjectPath)) {
    throw "WinUI project not found: $ProjectPath"
}

$SdkList = & dotnet --list-sdks 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($SdkList -join "`n"))) {
    throw ".NET SDK is required to build WinUI 3. Install .NET SDK 9, then rerun this script. Suggested command: winget install --id Microsoft.DotNet.SDK.9 --source winget"
}

if ($Clean) {
    if (Test-Path $DistRoot) {
        Remove-Item -LiteralPath $DistRoot -Recurse -Force
    }
    $BinRoot = Join-Path $ProjectRoot "bin"
    $ObjRoot = Join-Path $ProjectRoot "obj"
    if (Test-Path $BinRoot) {
        Remove-Item -LiteralPath $BinRoot -Recurse -Force
    }
    if (Test-Path $ObjRoot) {
        Remove-Item -LiteralPath $ObjRoot -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null

& dotnet publish $ProjectPath `
    --configuration Release `
    --runtime win-x64 `
    --property:WindowsPackageType=None `
    --property:RestoreConfigFile="$NuGetConfig" `
    --property:PublishDir="$DistRoot\"

if ($LASTEXITCODE -ne 0) {
    throw "WinUI 3 shell build failed with exit code $LASTEXITCODE"
}

$BuildOutput = Join-Path $ProjectRoot "bin\Release\net9.0-windows10.0.19041.0\win-x64"
if (Test-Path $BuildOutput) {
    Get-ChildItem -Path $BuildOutput -Include *.xbf,*.pri -File -Recurse | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $DistRoot $_.Name) -Force
    }
}

$ExePath = Join-Path $DistRoot "ModForge.WinUI.exe"
if (-not (Test-Path $ExePath)) {
    $ExePath = Get-ChildItem -Path $DistRoot -Filter *.exe -File -Recurse | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $ExePath) {
    throw "WinUI 3 build completed but no executable was found under $DistRoot"
}

$RequiredPackageFiles = @(
    "ModForge.WinUI.exe",
    "ModForge.WinUI.dll",
    "ModForge.WinUI.pri",
    "App.xbf",
    "MainWindow.xbf"
)
foreach ($RequiredPackageFile in $RequiredPackageFiles) {
    $RequiredPath = Join-Path $DistRoot $RequiredPackageFile
    if (-not (Test-Path $RequiredPath)) {
        throw "WinUI 3 package check failed. Missing required file: $RequiredPath"
    }
}

$BuildInfo = @(
    "ModForge.WinUI build",
    "Built: $(Get-Date -Format o)",
    "SDK: $($SdkList -join '; ')",
    "Output: $ExePath",
    "Package check: required exe, dll, pri, and xbf files present.",
    "Note: WinUI 3 primary candidate shell uses Microsoft.WindowsAppSDK and requires .NET SDK tooling."
)
$BuildInfo | Set-Content -LiteralPath (Join-Path $DistRoot "build-info.txt") -Encoding ASCII

Write-Host "Built $ExePath"
