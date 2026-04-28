param(
    [string]$Owner = "gsosystem2026",
    [string]$Repo = "gsosystem",
    [string]$WorkflowFile = "nightly-neon-backup.yml",
    [string]$ArtifactPrefix = "neon-pg-backup-",
    [string]$ProjectDir = "C:\Users\CLIENT\Desktop\GSO Final System 2026",
    [string]$ArchiveDir = "",
    [int]$KeepDays = 365
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ApiHeaders {
    $token = $env:GITHUB_BACKUP_PAT
    if (-not $token) {
        throw "Missing GITHUB_BACKUP_PAT environment variable. Create a GitHub token with repo + actions:read scope."
    }
    return @{
        "Accept" = "application/vnd.github+json"
        "Authorization" = "Bearer $token"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
}

function Get-LatestSuccessfulRun {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$WorkflowFile,
        [hashtable]$Headers
    )
    $url = "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$WorkflowFile/runs?status=success&per_page=10"
    $response = Invoke-RestMethod -Method Get -Uri $url -Headers $Headers
    if (-not $response.workflow_runs -or $response.workflow_runs.Count -eq 0) {
        throw "No successful workflow runs found for $WorkflowFile."
    }
    return $response.workflow_runs[0]
}

function Get-LatestArtifact {
    param(
        [string]$Owner,
        [string]$Repo,
        [long]$RunId,
        [string]$ArtifactPrefix,
        [hashtable]$Headers
    )
    $url = "https://api.github.com/repos/$Owner/$Repo/actions/runs/$RunId/artifacts?per_page=100"
    $response = Invoke-RestMethod -Method Get -Uri $url -Headers $Headers
    if (-not $response.artifacts -or $response.artifacts.Count -eq 0) {
        throw "No artifacts found for workflow run id $RunId."
    }
    $artifact = $response.artifacts |
        Where-Object { -not $_.expired -and $_.name -like "$ArtifactPrefix*" } |
        Sort-Object -Property created_at -Descending |
        Select-Object -First 1
    if (-not $artifact) {
        throw "No non-expired artifacts found with prefix '$ArtifactPrefix' for run id $RunId."
    }
    return $artifact
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Prune-OldArchives {
    param(
        [string]$ArchiveDir,
        [int]$KeepDays
    )
    $cutoff = (Get-Date).AddDays(-1 * $KeepDays)
    Get-ChildItem -Path $ArchiveDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Recurse -Force
            Write-Host "Pruned old archive: $($_.FullName)"
        }
}

$headers = Get-ApiHeaders
if (-not $ArchiveDir) {
    $ArchiveDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "GSO Backup"
}
Ensure-Directory -Path $ArchiveDir

$run = Get-LatestSuccessfulRun -Owner $Owner -Repo $Repo -WorkflowFile $WorkflowFile -Headers $headers
$artifact = Get-LatestArtifact -Owner $Owner -Repo $Repo -RunId $run.id -ArtifactPrefix $ArtifactPrefix -Headers $headers

$artifactFolder = Join-Path $ArchiveDir $artifact.name
$markerFile = Join-Path $artifactFolder ".artifact_id"
if ((Test-Path -LiteralPath $markerFile) -and ((Get-Content -LiteralPath $markerFile -Raw).Trim() -eq "$($artifact.id)")) {
    Write-Host "Latest artifact already archived: $($artifact.name) (id=$($artifact.id))"
    Prune-OldArchives -ArchiveDir $ArchiveDir -KeepDays $KeepDays
    exit 0
}

Ensure-Directory -Path $artifactFolder
$zipPath = Join-Path $artifactFolder "$($artifact.name).zip"
$downloadHeaders = @{
    "Authorization" = "Bearer $($env:GITHUB_BACKUP_PAT)"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}
Invoke-WebRequest -Uri $artifact.archive_download_url -Headers $downloadHeaders -OutFile $zipPath

$extractPath = Join-Path $artifactFolder "contents"
if (Test-Path -LiteralPath $extractPath) {
    Remove-Item -LiteralPath $extractPath -Recurse -Force
}
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
Set-Content -LiteralPath $markerFile -Value "$($artifact.id)" -NoNewline

Write-Host "Archived artifact to: $artifactFolder"
Write-Host "Extracted files path: $extractPath"

Prune-OldArchives -ArchiveDir $ArchiveDir -KeepDays $KeepDays
