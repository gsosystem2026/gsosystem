param(
    [string]$TaskName = "GSO_Sync_GitHub_Backup_Artifact_Daily_3AM",
    [string]$ProjectDir = "C:\Users\CLIENT\Desktop\GSO Final System 2026",
    [string]$ScriptRelativePath = "scripts\sync_github_backup_artifact.ps1",
    [string]$Owner = "gsosystem2026",
    [string]$Repo = "gsosystem",
    [int]$KeepDays = 365
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $ProjectDir $ScriptRelativePath
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Sync script not found: $scriptPath"
}

$token = [Environment]::GetEnvironmentVariable("GITHUB_BACKUP_PAT", "User")
if (-not $token) {
    throw "User environment variable GITHUB_BACKUP_PAT is not set. Set it first, then re-run this script."
}

$psArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-Owner", "`"$Owner`"",
    "-Repo", "`"$Repo`"",
    "-KeepDays", "$KeepDays"
) -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Download latest successful GitHub Nightly Neon Backup artifact to local archive." `
    -Force | Out-Null

Write-Host "Scheduled task created/updated: $TaskName"
Write-Host "Test it now with:"
Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`""
