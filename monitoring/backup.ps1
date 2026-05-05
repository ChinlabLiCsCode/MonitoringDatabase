# InfluxDB daily backup script.
# Runs influx backup inside the container, copies the result to C:/InfluxDB/backups/,
# and deletes backups older than $RetainDays days.
#
# Schedule via Windows Task Scheduler — see MIGRATION.md for instructions.

param(
    [int]$RetainDays = 30
)

$ErrorActionPreference = "Stop"

$Token     = (Get-Content "C:/Users/lics/Desktop/DatabaseDevelopment/configs/influxdb_credentials.json" | ConvertFrom-Json).token
$Date      = Get-Date -Format "yyyy-MM-dd"
$BackupDir = "C:/InfluxDB/backups"
$LogFile   = "$BackupDir/backup.log"
$ContainerPath = "/tmp/influx-backup-$Date"
$HostPath      = "$BackupDir/backup-$Date"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Write-Log "Starting backup for $Date"

# Run influx backup inside the running container
docker exec influxdb influx backup $ContainerPath `
    --host http://localhost:8086 `
    --token $Token

if (-not $?) {
    Write-Log "ERROR: influx backup failed"
    exit 1
}
Write-Log "Backup written inside container at $ContainerPath"

# Copy out of the container
if (Test-Path $HostPath) { Remove-Item -Recurse -Force $HostPath }
docker cp "influxdb:$ContainerPath" $HostPath

if (-not $?) {
    Write-Log "ERROR: docker cp failed"
    exit 1
}
Write-Log "Copied to $HostPath"

# Clean up temp files inside the container
docker exec influxdb rm -rf $ContainerPath

# Delete backups older than $RetainDays
$Cutoff = (Get-Date).AddDays(-$RetainDays)
Get-ChildItem -Path $BackupDir -Directory -Filter "backup-*" | Where-Object {
    $_.LastWriteTime -lt $Cutoff
} | ForEach-Object {
    Write-Log "Removing old backup: $($_.Name)"
    Remove-Item -Recurse -Force $_.FullName
}

Write-Log "Backup complete."
