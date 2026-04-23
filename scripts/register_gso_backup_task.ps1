param(
    [string]$TaskName = "GSO_AutoBackup_Weekdays_5PM",
    [string]$ProjectDir = "C:\Users\CLIENT\Desktop\GSO Final System 2026",
    [string]$RunScript = "scripts\run_gso_backup.bat"
)

$scriptPath = Join-Path $ProjectDir $RunScript
if (-not (Test-Path $scriptPath)) {
    throw "Backup runner script not found: $scriptPath"
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 5:00PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Run GSO database backup every weekday at 5PM." -Force

Write-Host "Scheduled task created/updated: $TaskName"
Write-Host "Run once now to test:"
Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`""
