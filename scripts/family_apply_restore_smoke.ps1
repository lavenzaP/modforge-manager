Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PreviousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
    Join-Path $RepoRoot "src"
}
else {
    "$(Join-Path $RepoRoot "src");$PreviousPythonPath"
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("modforge-family-apply-" + [System.Guid]::NewGuid().ToString("N"))

function Get-ProbeSignature {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return "<missing>"
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Invoke-FamilySmoke {
    param(
        [string]$Family,
        [string]$Profile,
        [string]$ProbePath,
        [switch]$SeedProbe
    )

    $CaseRoot = Join-Path $TempRoot $Family
    $GameRoot = Join-Path $CaseRoot "game"
    $ModsRoot = Join-Path $CaseRoot "mods"
    $ProjectFile = Join-Path $CaseRoot "modforge.project.json"
    $StagingRoot = Join-Path $CaseRoot ".modforge\staging"
    $FixtureRoot = Join-Path $RepoRoot "tests\fixtures\mod_families\$Family"
    $Probe = Join-Path $GameRoot $ProbePath

    New-Item -ItemType Directory -Path $CaseRoot -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $FixtureRoot "fake_game") -Destination $GameRoot -Recurse
    Copy-Item -LiteralPath (Join-Path $FixtureRoot "mods") -Destination $ModsRoot -Recurse

    $OriginalProbeSignature = "<missing>"
    if ($SeedProbe) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Probe) -Force | Out-Null
        "original $Family probe" | Set-Content -LiteralPath $Probe -Encoding UTF8
        $OriginalProbeSignature = Get-ProbeSignature -Path $Probe
    }

    & python -m modforge project init --name "Family $Family" --game-root $GameRoot --mods-dir $ModsRoot --staging-dir $StagingRoot --profile $Profile --project-file $ProjectFile | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "$Family project init failed with exit code $LASTEXITCODE"
    }

    $Scan = & python -m modforge scan-mods --project-file $ProjectFile --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family scan failed with exit code $LASTEXITCODE"
    }
    if ($Scan.Count -lt 1) {
        throw "$Family scan returned no packages"
    }

    $Plan = & python -m modforge plan --project-file $ProjectFile --summary --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family plan failed with exit code $LASTEXITCODE"
    }
    if (-not $Plan.dry_run) {
        throw "$Family plan was not marked dry-run"
    }
    if ($Plan.operations -lt 1) {
        throw "$Family plan returned no operations"
    }

    $StagingManifest = & python -m modforge apply-staging --project-file $ProjectFile --yes --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family apply-staging failed with exit code $LASTEXITCODE"
    }
    if ($StagingManifest.target -ne "staging") {
        throw "$Family apply-staging returned unexpected target $($StagingManifest.target)"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $StagingRoot ".modforge-install-manifest.json"))) {
        throw "$Family staging manifest was not created"
    }

    $GameManifest = & python -m modforge apply-game --project-file $ProjectFile --yes --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family apply-game failed with exit code $LASTEXITCODE"
    }
    if ($GameManifest.target -ne "game") {
        throw "$Family apply-game returned unexpected target $($GameManifest.target)"
    }
    if (-not (Test-Path -LiteralPath $Probe)) {
        throw "$Family probe was not applied: $ProbePath"
    }
    if ($SeedProbe -and $GameManifest.backups.Count -lt 1) {
        throw "$Family did not record a backup for the seeded overwrite"
    }

    $ManifestPath = Join-Path (Join-Path $CaseRoot ".modforge\manifests") "$($GameManifest.manifest_id).json"
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        throw "$Family game manifest was not created"
    }

    $Latest = & python -m modforge manifests latest --project-file $ProjectFile --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family manifests latest failed with exit code $LASTEXITCODE"
    }
    if ($Latest.manifest_id -ne $GameManifest.manifest_id) {
        throw "$Family latest manifest did not match game apply manifest"
    }

    $Shown = & python -m modforge manifests show $GameManifest.manifest_id --project-file $ProjectFile --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family manifests show failed with exit code $LASTEXITCODE"
    }
    if ($Shown.manifest_id -ne $GameManifest.manifest_id) {
        throw "$Family manifest show returned the wrong manifest"
    }

    $BeforePreviewSignature = Get-ProbeSignature -Path $Probe
    $Preview = & python -m modforge restore --project-file $ProjectFile --manifest $ManifestPath --preview --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "$Family restore preview failed with exit code $LASTEXITCODE"
    }
    if (-not $Preview.can_restore) {
        throw "$Family restore preview was blocked"
    }
    if ((Get-ProbeSignature -Path $Probe) -ne $BeforePreviewSignature) {
        throw "$Family restore preview mutated the probe"
    }

    & python -m modforge restore --project-file $ProjectFile --manifest $ManifestPath --yes --json | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "$Family restore failed with exit code $LASTEXITCODE"
    }

    $AfterRestoreSignature = Get-ProbeSignature -Path $Probe
    if ($SeedProbe) {
        if ($AfterRestoreSignature -ne $OriginalProbeSignature) {
            throw "$Family restore did not return the seeded probe to its original content"
        }
    }
    elseif ($AfterRestoreSignature -ne "<missing>") {
        throw "$Family restore left a manifest-created probe in place: $ProbePath"
    }
}

try {
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    Invoke-FamilySmoke -Family "reframework_wilds" -Profile "mhw-reframework" -ProbePath "reframework\data\BoneSystem\monster_a.json" -SeedProbe
    Invoke-FamilySmoke -Family "unreal_pak" -Profile "unreal-pak" -ProbePath "Content\Paks\~mods\TextureTriplet_P.pak"
    Invoke-FamilySmoke -Family "godot_sts2" -Profile "sts2-mods" -ProbePath "mods\BetterCards\better_cards.pck"

    Write-Host "Family apply/restore smoke passed: REFramework overwrite backup, Unreal sidecar, and Godot/STS2 fake roots staged, applied, inspected, previewed, and restored."
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
