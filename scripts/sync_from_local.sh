#!/usr/bin/env bash
set -e

# ==============================================================================
# Script: sync_from_local.sh
# Description: Synchronize changes from dora_based_openarm_teleop_local (Local Gitea/GitLab Repo)
#              to dora_based_openarm_teleop (GitHub Main Repo).
# Usage: ./scripts/sync_from_local.sh [--dry-run]
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="$(cd "${TARGET_DIR}/../dora_based_openarm_teleop_local" 2>/dev/null && pwd || echo "")"

if [ -z "${SOURCE_DIR}" ] || [ ! -d "${SOURCE_DIR}" ]; then
    echo "❌ Error: Source directory 'dora_based_openarm_teleop_local' not found at ${TARGET_DIR}/../dora_based_openarm_teleop_local"
    exit 1
fi

DRY_RUN=""
if [ "$1" == "--dry-run" ] || [ "$1" == "-n" ]; then
    DRY_RUN="--dry-run"
    echo "🔍 Executing in DRY-RUN mode (No files will be modified)..."
fi

echo "🔄 Synchronizing: [Local Repo] ${SOURCE_DIR}/ -> [Main Repo] ${TARGET_DIR}/"

rsync -av ${DRY_RUN} \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='env' \
    --exclude='ENV' \
    --exclude='build' \
    --exclude='install' \
    --exclude='log' \
    --exclude='out' \
    --exclude='.cache' \
    --exclude='.obsidian' \
    --exclude='.pytest_cache' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "${SOURCE_DIR}/" "${TARGET_DIR}/"

echo "✅ Sync from Local Repo to Main Repo completed successfully!"
