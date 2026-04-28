param(
    [string]$DumpPath = "",
    [string]$TargetDatabaseUrl = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-PgRestore {
    $pgCmd = Get-Command pg_restore -ErrorAction SilentlyContinue
    if ($pgCmd) {
        return $pgCmd.Source
    }

    $pgBin = [Environment]::GetEnvironmentVariable("PG_BIN_DIR", "User")
    if ($pgBin) {
        $candidate = Join-Path $pgBin "pg_restore.exe"
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "pg_restore not found. Install PostgreSQL client tools or set User env var PG_BIN_DIR to PostgreSQL bin folder."
}

function Resolve-DumpPath {
    param([string]$InputPath)
    if (-not $InputPath) {
        $InputPath = Read-Host "Enter full path to backup file (.dump or .zip)"
    }
    if (-not (Test-Path -LiteralPath $InputPath)) {
        throw "File not found: $InputPath"
    }

    $ext = [System.IO.Path]::GetExtension($InputPath).ToLowerInvariant()
    if ($ext -eq ".dump") {
        return $InputPath
    }
    if ($ext -ne ".zip") {
        throw "Unsupported file type. Use .dump or .zip downloaded from GitHub artifact."
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("gso-restore-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Expand-Archive -LiteralPath $InputPath -DestinationPath $tempRoot -Force
    $dump = Get-ChildItem -Path $tempRoot -Filter *.dump -Recurse | Select-Object -First 1
    if (-not $dump) {
        throw "No .dump file found inside zip: $InputPath"
    }
    return $dump.FullName
}

Write-Host "=== GSO Guided Rollback (Dump Restore) ==="
Write-Host ""
Write-Host "This tool restores a selected backup dump to a target PostgreSQL database."
Write-Host "Tip: restore to a Neon rollback branch first, then switch Render DATABASE_URL to that branch."
Write-Host ""

$resolvedDump = Resolve-DumpPath -InputPath $DumpPath
if (-not $TargetDatabaseUrl) {
    $TargetDatabaseUrl = Read-Host "Enter target DATABASE_URL (Neon branch URL)"
}
if (-not $TargetDatabaseUrl) {
    throw "Target DATABASE_URL is required."
}

$confirm = Read-Host "Proceed restore to target database? Type YES to continue"
if ($confirm -cne "YES") {
    Write-Host "Cancelled. No changes were made."
    exit 0
}

$pgRestore = Find-PgRestore
Write-Host ""
Write-Host "Using dump: $resolvedDump"
Write-Host "Running pg_restore..."

& $pgRestore --clean --if-exists --no-owner --no-privileges -d $TargetDatabaseUrl $resolvedDump
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Restore completed successfully."
Write-Host "Next step: In Render, set DATABASE_URL to this target URL and redeploy/restart service."
