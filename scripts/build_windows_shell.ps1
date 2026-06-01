param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $RepoRoot "desktop\ModForge.App"
$DistRoot = Join-Path $RepoRoot "dist\ModForge.App"
$ObjRoot = Join-Path $RepoRoot "build\ModForge.App"
$ExePath = Join-Path $DistRoot "ModForge.App.exe"

if ($Clean) {
    if (Test-Path $DistRoot) {
        Remove-Item -LiteralPath $DistRoot -Recurse -Force
    }
    if (Test-Path $ObjRoot) {
        Remove-Item -LiteralPath $ObjRoot -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $DistRoot, $ObjRoot -Force | Out-Null

$RoslynCsc = "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\Roslyn\csc.exe"
$FrameworkCsc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"

if (Test-Path $RoslynCsc) {
    $Csc = $RoslynCsc
} elseif (Test-Path $FrameworkCsc) {
    $Csc = $FrameworkCsc
} else {
    throw "Could not find csc.exe. Install Visual Studio Build Tools or the .NET Framework compiler."
}

$Framework = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319"
$Wpf = Join-Path $Framework "WPF"
$References = @(
    (Join-Path $Framework "System.dll"),
    (Join-Path $Framework "System.Core.dll"),
    (Join-Path $Framework "System.Xaml.dll"),
    (Join-Path $Framework "Microsoft.CSharp.dll"),
    (Join-Path $Wpf "WindowsBase.dll"),
    (Join-Path $Wpf "PresentationCore.dll"),
    (Join-Path $Wpf "PresentationFramework.dll"),
    (Join-Path $Wpf "PresentationFramework.Aero2.dll")
)

foreach ($Reference in $References) {
    if (-not (Test-Path $Reference)) {
        throw "Missing .NET/WPF reference: $Reference"
    }
}

$Sources = Get-ChildItem -Path $SourceRoot -Filter *.cs -File | Sort-Object Name | ForEach-Object { $_.FullName }
if ($Sources.Count -eq 0) {
    throw "No C# sources found under $SourceRoot"
}

$Args = @(
    "/nologo",
    "/target:winexe",
    "/platform:x64",
    "/optimize+",
    "/warn:4",
    "/out:$ExePath",
    "/main:ModForge.App.Program"
)

foreach ($Reference in $References) {
    $Args += "/reference:$Reference"
}

$Args += $Sources

& $Csc @Args
if ($LASTEXITCODE -ne 0) {
    throw "WPF shell build failed with exit code $LASTEXITCODE"
}

$BuildInfo = @(
    "ModForge.App build",
    "Built: $(Get-Date -Format o)",
    "Compiler: $Csc",
    "Output: $ExePath",
    "Note: Milestone 6B shell does not launch Python at startup."
)
$BuildInfo | Set-Content -LiteralPath (Join-Path $DistRoot "build-info.txt") -Encoding ASCII

Write-Host "Built $ExePath"
