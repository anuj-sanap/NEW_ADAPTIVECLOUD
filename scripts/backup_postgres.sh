#!/usr/bin/env bash
# ==============================================================================
# scripts/backup_postgres.sh
# Automated PostgreSQL Backup, Gzip Compression, and 7-Day Retention Script.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${CONTAINER_NAME:-}"

mkdir -p "${BACKUP_DIR}"

if [[ -z "${CONTAINER_NAME}" ]]; then
    if docker ps --format '{{.Names}}' | grep -q "adaptivecloud-postgres-prod"; then
        CONTAINER_NAME="adaptivecloud-postgres-prod"
    elif docker ps --format '{{.Names}}' | grep -q "adaptivecloud-postgres"; then
        CONTAINER_NAME="adaptivecloud-postgres"
    else
        CONTAINER_NAME="adaptivecloud-postgres"
    fi
fi

echo "========================================================================"
echo "   ADAPTIVECLOUD - POSTGRESQL BACKUP & DISASTER RECOVERY UTILITY        "
echo "========================================================================"
echo "[*] Container: ${CONTAINER_NAME}"
echo "[*] Backup Directory: ${BACKUP_DIR}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/adaptivecloud_db_${TIMESTAMP}.sql.gz"

echo "[*] Dumping and compressing PostgreSQL database..."
docker exec "${CONTAINER_NAME}" pg_dump -U postgres --clean --if-exists adaptivecloud | gzip > "${BACKUP_FILE}"

if [[ -s "${BACKUP_FILE}" ]]; then
    FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[+] Backup successfully created: ${BACKUP_FILE} (${FILE_SIZE})"
else
    echo "[!] Backup failed or file is empty!" >&2
    exit 1
fi

echo "[*] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "adaptivecloud_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -print -delete
echo "[+] Pruning complete."

