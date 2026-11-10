<#
.SYNOPSIS
    Automated PostgreSQL Backup and Retention Script for AdaptiveCloud.
    Supports pg_dump via Docker, gzip compression, and 7-day retention pruning.
.PARAMETER BackupDir
    Directory where backups will be stored (default: repo_root/backups)
.PARAMETER RetentionDays
    Number of days to retain backups before automated pruning (default: 7)
.PARAMETER ContainerName
    Postgres container name (default: auto-detect adaptivecloud-postgres / adaptivecloud-postgres-prod)
.PARAMETER RestoreFile
    Optional path to .sql or .sql.gz file to restore into database
#>
[CmdletBinding()]
param(
    [string]$BackupDir = "$PSScriptRoot\..\backups",
    [int]$RetentionDays = 7,
    [string]$ContainerName = "",
    [string]$RestoreFile = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}
$ResolvedBackupDir = (Resolve-Path $BackupDir).Path

# Auto-detect running postgres container if not specified
if (-not $ContainerName) {
    $runningContainers = docker ps --format "{{.Names}}" 2>$null
    if ($runningContainers -match "adaptivecloud-postgres-prod") {
        $ContainerName = "adaptivecloud-postgres-prod"
    } elseif ($runningContainers -match "adaptivecloud-postgres") {
        $ContainerName = "adaptivecloud-postgres"
    } else {
        $ContainerName = "adaptivecloud-postgres"
    }
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   ADAPTIVECLOUD - POSTGRESQL BACKUP & DISASTER RECOVERY UTILITY        " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "[*] Target Container: $ContainerName" -ForegroundColor Yellow
Write-Host "[*] Backup Directory: $ResolvedBackupDir" -ForegroundColor Yellow

# RESTORE MODE
if ($RestoreFile) {
    if (-not (Test-Path $RestoreFile)) {
        Write-Error "Restore target file not found: $RestoreFile"
    }
    Write-Host "[!] RESTORE INITIATED: Restoring from $RestoreFile into $ContainerName..." -ForegroundColor Red
    if ($RestoreFile.EndsWith(".gz")) {
        Get-Content $RestoreFile -Raw -Encoding Byte | docker exec -i $ContainerName bash -c "gunzip | psql -U postgres -d adaptivecloud"
    } else {
        Get-Content $RestoreFile -Raw | docker exec -i $ContainerName psql -U postgres -d adaptivecloud
    }
    Write-Host "[+] Database successfully restored from $RestoreFile" -ForegroundColor Green
    exit 0
}

# BACKUP MODE
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$backupFileName = "adaptivecloud_db_${timestamp}.sql"
$backupFilePath = Join-Path $ResolvedBackupDir $backupFileName

Write-Host "[*] Streaming pg_dump from container..." -ForegroundColor Yellow
$dumpCmd = "docker exec -i $ContainerName pg_dump -U postgres --clean --if-exists adaptivecloud"
Invoke-Expression $dumpCmd | Out-File -FilePath $backupFilePath -Encoding utf8

if ((Test-Path $backupFilePath) -and (Get-Item $backupFilePath).Length -gt 0) {
    $sizeKb = [math]::Round((Get-Item $backupFilePath).Length / 1KB, 1)
    Write-Host "[+] Raw backup successfully created: $backupFileName ($sizeKb KB)" -ForegroundColor Green

    # Attempt gzip compression if 7z or tar or gzip is available
    $gzip = Get-Command gzip -ErrorAction SilentlyContinue
    if ($gzip) {
        & gzip -f $backupFilePath
        $gzPath = "$backupFilePath.gz"
        if (Test-Path $gzPath) {
            $gzSizeKb = [math]::Round((Get-Item $gzPath).Length / 1KB, 1)
            Write-Host "[+] Compressed with gzip: ${backupFileName}.gz ($gzSizeKb KB)" -ForegroundColor Green
        }
    }
} else {
    Write-Error "Backup failed or generated an empty file. Check container status: docker ps"
}

# RETENTION PRUNING
Write-Host "[*] Enforcing backup retention policy ($RetentionDays days)..." -ForegroundColor Yellow
$cutoffDate = (Get-Date).AddDays(-$RetentionDays)
$oldFiles = Get-ChildItem -Path $ResolvedBackupDir -Filter "adaptivecloud_db_*.sql*" | Where-Object { $_.LastWriteTime -lt $cutoffDate }

$prunedCount = 0
foreach ($file in $oldFiles) {
    Write-Host "[-] Pruning expired backup: $($file.Name) ($($file.LastWriteTime.ToString('yyyy-MM-dd')))" -ForegroundColor DarkGray
    Remove-Item $file.FullName -Force
    $prunedCount++
}

Write-Host "[+] Retention sweep complete: $prunedCount expired backup(s) pruned." -ForegroundColor Green
Write-Host ">>> POSTGRESQL BACKUP COMPLETED CLEANLY." -ForegroundColor Cyan
