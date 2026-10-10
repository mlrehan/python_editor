#!/bin/bash
# ========================================================
# Python Cloud Studio - Automated Restore Script
# Restores PostgreSQL DB and User Workspaces from an archive
# ========================================================
set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore.sh <path-to-pcs_backup_*.tar.gz>"
    exit 1
fi

ARCHIVE_PATH="$1"

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "Error: Backup file not found: ${ARCHIVE_PATH}"
    exit 1
fi

TEMP_RESTORE_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_RESTORE_DIR}"' EXIT

# Load .env variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_USER="${POSTGRES_USER:-pcs_user}"
DB_NAME="${POSTGRES_DB:-python_cloud_studio}"
DB_PORT="${POSTGRES_PORT:-5476}"

echo "=========================================================="
echo "Restoring Python Cloud Studio from: ${ARCHIVE_PATH}"
echo "=========================================================="

# 1. Unpack archive
echo "[1/4] Unpacking archive..."
tar -xzf "${ARCHIVE_PATH}" -C "${TEMP_RESTORE_DIR}"
BACKUP_FOLDER=$(find "${TEMP_RESTORE_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)

if [ ! -d "${BACKUP_FOLDER}" ]; then
    echo "Error: Corrupted archive structure."
    exit 1
fi

# 2. Stop API to avoid file locks
echo "[2/4] Pausing application API container..."
docker compose stop api

# 3. Restore PostgreSQL Database
echo "[3/4] Restoring PostgreSQL database..."
if [ -f "${BACKUP_FOLDER}/database.sql" ]; then
    docker compose exec -T postgres psql -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FOLDER}/database.sql"
else
    echo "Warning: database.sql not found in archive. Skipping DB restore."
fi

# 4. Restore Workspaces & Files
echo "[4/4] Restoring user workspaces and notebooks..."
if [ -f "${BACKUP_FOLDER}/workspaces.tar.gz" ]; then
    docker run --rm \
        --volumes-from pcs-api \
        -v "${BACKUP_FOLDER}:/backup_src" \
        alpine tar -xzf /backup_src/workspaces.tar.gz -C /app/storage
fi

# 5. Restart application
docker compose start api

echo "=========================================================="
echo "✔ Restore completed successfully!"
echo "Python Cloud Studio services are restored and running."
echo "=========================================================="

