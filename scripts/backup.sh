#!/bin/bash
# ========================================================
# Python Cloud Studio - Automated Backup Script
# Creates a compressed archive of PostgreSQL DB and User Workspaces
# ========================================================
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TARGET_DIR="${BACKUP_DIR}/backup_${TIMESTAMP}"

mkdir -p "${TARGET_DIR}"

# Load .env variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_USER="${POSTGRES_USER:-pcs_user}"
DB_NAME="${POSTGRES_DB:-python_cloud_studio}"

echo "=========================================================="
echo "Starting Python Cloud Studio Backup [${TIMESTAMP}]"
echo "Target: ${TARGET_DIR}"
echo "=========================================================="

# 1. Backup PostgreSQL Database
echo "[1/3] Dumping PostgreSQL database..."
docker compose exec -T postgres pg_dump -U "${DB_USER}" "${DB_NAME}" > "${TARGET_DIR}/database.sql"

# 2. Backup User Workspaces & Notebooks
echo "[2/3] Archiving user workspaces and notebooks..."
docker run --rm \
    --volumes-from pcs-api \
    -v "${TARGET_DIR}:/backup_dest" \
    alpine tar -czf /backup_dest/workspaces.tar.gz -C /app/storage workspaces artifacts

# 3. Compress entire backup
echo "[3/3] Creating final compressed archive..."
cd "${BACKUP_DIR}"
tar -czf "pcs_backup_${TIMESTAMP}.tar.gz" "backup_${TIMESTAMP}"
rm -rf "backup_${TIMESTAMP}"

echo "=========================================================="
echo "✔ Backup completed successfully!"
echo "Archive saved to: ${BACKUP_DIR}/pcs_backup_${TIMESTAMP}.tar.gz"
echo "=========================================================="

