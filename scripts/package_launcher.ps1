Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_launcher.ps1"
$Dist = Join-Path $RepoRoot "dist\ModForge.Launcher"
$Version = "v0.1.2-preview.1"
$Zip = Join-Path $RepoRoot "dist\ModForge.Manager-$Version-win-x64.zip"

& $BuildScript -SelfContained

Copy-Item -LiteralPath (Join-Path $RepoRoot "LICENSE") -Destination (Join-Path $Dist "LICENSE.txt") -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "README.md") -Destination (Join-Path $Dist "README.md") -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot "README.ko.md") -Destination (Join-Path $Dist "README.ko.md") -Force

$StartHere = @"
ModForge Manager v0.1.2 Preview 1

1. Run ModForge.Launcher.exe.
2. Add or select your Unreal game folder.
3. Drag mod archives, mod folders, or .pak/.ucas/.utoc files into the app.
4. Turn mods on or off.
5. Press Apply Changes, then Launch Game.

This is a self-contained portable preview. You do not need Visual Studio, the
.NET SDK, or a build step. Windows SmartScreen may warn because the app is
unsigned. Normal use should not require administrator rights unless your game
folder blocks writes.

Preview limits: no installer, no Nexus downloads, Unreal/UE4SS-focused.
"@
Set-Content -LiteralPath (Join-Path $Dist "START_HERE.txt") -Value $StartHere -Encoding UTF8

if (Test-Path $Zip) {
    Remove-Item -LiteralPath $Zip -Force
}

Compress-Archive -Path (Join-Path $Dist "*") -DestinationPath $Zip -CompressionLevel Optimal

Add-Type -AssemblyName System.IO.Compression.FileSystem
$Archive = [System.IO.Compression.ZipFile]::OpenRead($Zip)
try {
    if (-not ($Archive.Entries | Where-Object { $_.FullName -eq "ModForge.Launcher.exe" })) {
        throw "Package does not contain ModForge.Launcher.exe"
    }
}
finally {
    $Archive.Dispose()
}

$Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Zip).Hash
Write-Host "Packaged $Zip"
Write-Host "SHA256 $Hash"
