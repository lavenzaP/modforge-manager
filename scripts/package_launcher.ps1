Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_launcher.ps1"
$Dist = Join-Path $RepoRoot "dist\ModForge.Launcher"
$Zip = Join-Path $RepoRoot "dist\ModForge.Launcher-win-x64.zip"

& $BuildScript

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
