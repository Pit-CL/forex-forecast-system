#!/bin/bash
#
# Automatic Docker Cleanup Script
#
# This script monitors disk usage and automatically cleans Docker when usage exceeds threshold.
# Designed to run via cron to maintain healthy disk space.
#
# Usage:
#   ./scripts/auto_cleanup_docker.sh [threshold]
#
# Cron example (runs daily at 2 AM):
#   0 2 * * * /home/deployer/forex-forecast-system/scripts/auto_cleanup_docker.sh >> /home/deployer/forex-forecast-system/logs/docker_cleanup.log 2>&1
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default threshold: 85%
THRESHOLD=${1:-85}

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Docker Auto-Cleanup Check - $(date)"
echo "=========================================="
echo ""

# Get current disk usage percentage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

echo "Current disk usage: ${DISK_USAGE}%"
echo "Cleanup threshold: ${THRESHOLD}%"
echo ""

if [ "$DISK_USAGE" -ge "$THRESHOLD" ]; then
    echo "⚠️  Disk usage (${DISK_USAGE}%) exceeds threshold (${THRESHOLD}%)"
    echo "Starting automatic Docker cleanup..."
    echo ""

    # Get disk space before cleanup
    DISK_BEFORE=$(df / | tail -1 | awk '{print $3}')

    echo "Step 1/2: Cleaning Docker build cache..."
    docker builder prune -a -f | tail -1
    echo ""

    echo "Step 2/2: Removing unused Docker images..."
    docker image prune -a -f | tail -1
    echo ""

    # Get disk space after cleanup
    DISK_AFTER=$(df / | tail -1 | awk '{print $3}')
    DISK_USAGE_AFTER=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

    # Calculate space freed (in KB, convert to GB)
    SPACE_FREED=$(echo "scale=2; ($DISK_BEFORE - $DISK_AFTER) / 1024 / 1024" | bc)

    echo "=========================================="
    echo "✅ Cleanup completed successfully"
    echo "=========================================="
    echo "Disk usage before: ${DISK_USAGE}%"
    echo "Disk usage after:  ${DISK_USAGE_AFTER}%"
    echo "Space freed:       ${SPACE_FREED}GB"
    echo ""

    # Verify disk usage decreased
    if [ "$DISK_USAGE_AFTER" -lt "$DISK_USAGE" ]; then
        echo "✅ Disk usage successfully reduced"
    else
        echo "⚠️  Warning: Disk usage did not decrease significantly"
    fi

else
    echo "✅ Disk usage is healthy (${DISK_USAGE}% < ${THRESHOLD}%)"
    echo "No cleanup needed at this time"
fi

echo ""
echo "=========================================="
echo "Check complete - $(date)"
echo "=========================================="
