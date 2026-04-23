param(
    [string]$ProjectDir = "C:\Users\CLIENT\Desktop\GSO Final System 2026",
    [string]$DumpPath = ""
)

$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    throw ".env not found at $envFile"
}

$envMap = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        $envMap[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$databaseUrl = $envMap["DATABASE_URL"]
if (-not $databaseUrl) {
    throw "DATABASE_URL not found in .env"
}

$pgBinDir = $envMap["PG_BIN_DIR"]
if ($pgBinDir -and (Test-Path (Join-Path $pgBinDir "pg_restore.exe"))) {
    $env:Path = "$pgBinDir;$env:Path"
}

if (-not $DumpPath) {
    $backupDir = $envMap["GSO_BACKUP_DIR"]
    if (-not $backupDir) {
        $backupDir = Join-Path $ProjectDir "backups"
    }
    if (-not (Test-Path $backupDir)) {
        throw "Backup directory not found: $backupDir"
    }
    $latest = Get-ChildItem -Path $backupDir -Filter "pg_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        throw "No pg_*.dump file found in $backupDir"
    }
    $DumpPath = $latest.FullName
}

Write-Host "Using dump file: $DumpPath"
Write-Host "Starting restore..."

& pg_restore --clean --if-exists --no-owner --no-privileges -d $databaseUrl $DumpPath
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore failed with exit code $LASTEXITCODE"
}

Write-Host "Restore completed successfully."
