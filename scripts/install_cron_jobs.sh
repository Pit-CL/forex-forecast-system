#!/bin/bash
###############################################################################
# Install Cron Jobs for Forex Forecasting System
#
# This script installs cron jobs for automated tasks:
# - Weekly validation (Mondays at 9 AM)
# - Daily dashboard reports (Daily at 8 AM)
# - Performance monitoring (Daily at 10 AM)
#
# Usage:
#   ./scripts/install_cron_jobs.sh
#   ./scripts/install_cron_jobs.sh --uninstall  # To remove cron jobs
###############################################################################

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRON_MARKER="# Forex Forecasting System - Automated Jobs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Forex Forecasting System - Cron Setup${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Check if uninstall requested
if [ "$1" = "--uninstall" ]; then
    echo "Removing existing cron jobs..."

    # Remove lines between markers
    (crontab -l 2>/dev/null || true) | grep -v "${CRON_MARKER}" | grep -v "weekly_validation.sh" | grep -v "daily_dashboard.sh" | crontab - 2>/dev/null || true

    echo -e "${GREEN}✓ Cron jobs removed successfully${NC}"
    exit 0
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x "${PROJECT_DIR}/scripts/weekly_validation.sh"
chmod +x "${PROJECT_DIR}/scripts/daily_dashboard.sh" 2>/dev/null || echo -e "${YELLOW}⚠ daily_dashboard.sh not found yet${NC}"

# Get current crontab
CURRENT_CRON=$(crontab -l 2>/dev/null || true)

# Check if jobs already installed
if echo "${CURRENT_CRON}" | grep -q "${CRON_MARKER}"; then
    echo -e "${YELLOW}Cron jobs already installed. Updating...${NC}"
    # Remove old entries
    CURRENT_CRON=$(echo "${CURRENT_CRON}" | grep -v "${CRON_MARKER}" | grep -v "weekly_validation.sh" | grep -v "daily_dashboard.sh")
fi

# Create new cron entries
NEW_CRON="${CURRENT_CRON}

${CRON_MARKER}
# Weekly validation - Every Monday at 9:00 AM
0 9 * * 1 cd ${PROJECT_DIR} && ./scripts/weekly_validation.sh >> ${PROJECT_DIR}/logs/cron.log 2>&1

# Daily dashboard report - Every day at 8:00 AM
0 8 * * * cd ${PROJECT_DIR} && ./scripts/daily_dashboard.sh >> ${PROJECT_DIR}/logs/cron.log 2>&1

# Performance check - Every day at 10:00 AM
0 10 * * * cd ${PROJECT_DIR} && python scripts/check_performance.py --all >> ${PROJECT_DIR}/logs/cron.log 2>&1
"

# Install new crontab
echo "${NEW_CRON}" | crontab -

echo ""
echo -e "${GREEN}✓ Cron jobs installed successfully!${NC}"
echo ""
echo "Installed jobs:"
echo "  • Weekly Validation:     Mondays at 9:00 AM"
echo "  • Daily Dashboard:       Daily at 8:00 AM"
echo "  • Performance Check:     Daily at 10:00 AM"
echo ""
echo "Logs will be written to: ${PROJECT_DIR}/logs/cron.log"
echo ""
echo "To view installed cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove cron jobs:"
echo "  ./scripts/install_cron_jobs.sh --uninstall"
echo ""
echo -e "${YELLOW}Note: Ensure your .env file is configured with email settings${NC}"
echo -e "${YELLOW}      if you want email notifications.${NC}"
echo ""
