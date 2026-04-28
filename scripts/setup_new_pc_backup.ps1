param(
    [string]$Owner = "gsosystem2026",
    [string]$Repo = "gsosystem",
    [string]$TaskName = "GSO_Sync_GitHub_Backup_Artifact_Daily_3AM",
    [int]$KeepDays = 365
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== GSO Backup Kit: New PC Setup ==="
Write-Host ""

$inputOwner = Read-Host "GitHub owner [$Owner]"
if ($inputOwner) { $Owner = $inputOwner.Trim() }
$inputRepo = Read-Host "GitHub repo [$Repo]"
if ($inputRepo) { $Repo = $inputRepo.Trim() }

$secureToken = Read-Host "Paste GitHub PAT (input hidden)" -AsSecureString
$plainToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
)
if (-not $plainToken) {
    throw "GitHub PAT is required."
}

[Environment]::SetEnvironmentVariable("GITHUB_BACKUP_PAT", $plainToken, "User")
Write-Host "Saved user env var GITHUB_BACKUP_PAT."

$registerScript = Join-Path $PSScriptRoot "register_github_artifact_sync_task.ps1"
if (-not (Test-Path -LiteralPath $registerScript)) {
    throw "Missing register script: $registerScript"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $registerScript `
    -TaskName $TaskName `
    -KitDir $PSScriptRoot `
    -Owner $Owner `
    -Repo $Repo `
    -KeepDays $KeepDays

Write-Host ""
Write-Host "Running one immediate sync test..."

$syncScript = Join-Path $PSScriptRoot "sync_github_backup_artifact.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $syncScript `
    -Owner $Owner `
    -Repo $Repo `
    -KeepDays $KeepDays

Write-Host ""
Write-Host "Setup complete."
Write-Host "Local archive path: $([Environment]::GetFolderPath('MyDocuments'))\GSO Backup"
