#!/bin/bash
#
# Daily Chronos Readiness Check
#
# This script runs daily to check if the system is ready to enable Chronos.
# If ready, it sends a notification but does NOT auto-enable (requires manual approval).
#
# Usage:
#   ./scripts/daily_readiness_check.sh
#
# Cron example (runs daily at 9 AM):
#   0 9 * * * /app/scripts/daily_readiness_check.sh >> /app/logs/readiness_checks.log 2>&1

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Chronos Readiness Check - $(date)"
echo "=========================================="
echo ""

# Run readiness check
if python3 scripts/check_chronos_readiness.py check --data-dir data; then
    READINESS_STATUS="READY"
    EXIT_CODE=0
elif [ $? -eq 2 ]; then
    READINESS_STATUS="CAUTIOUS"
    EXIT_CODE=2
else
    READINESS_STATUS="NOT_READY"
    EXIT_CODE=1
fi

echo ""
echo "Status: $READINESS_STATUS (exit code: $EXIT_CODE)"
echo ""

# Save status to file for monitoring
echo "$READINESS_STATUS|$(date -Iseconds)" > data/chronos_readiness_status.txt

# If ready, log recommendation
if [ "$READINESS_STATUS" = "READY" ]; then
    echo "=========================================="
    echo "✅ SYSTEM READY FOR CHRONOS"
    echo "=========================================="
    echo ""
    echo "To enable Chronos foundation model:"
    echo "  1. Review readiness report above"
    echo "  2. Update .env: ENABLE_CHRONOS=true"
    echo "  3. Restart services: docker compose restart"
    echo ""
    echo "Or use auto-enable (with caution):"
    echo "  python3 scripts/check_chronos_readiness.py auto-enable"
    echo ""
fi

echo "=========================================="
echo "Check complete - $(date)"
echo "=========================================="
