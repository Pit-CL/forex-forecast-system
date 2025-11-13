#!/bin/bash
###############################################################################
# Weekly Validation Automation Script
#
# This script runs weekly model validation and sends results via email.
# Designed to be executed via cron job every Monday at 9 AM.
#
# Cron entry (add to crontab with: crontab -e):
# 0 9 * * 1 cd /path/to/forex-forecast-system && ./scripts/weekly_validation.sh
#
# Or for Vultr deployment:
# 0 9 * * 1 cd /home/forecast/forex-forecast-system && ./scripts/weekly_validation.sh
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
REPORT_DIR="${PROJECT_DIR}/reports/validation"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${LOG_DIR}/weekly_validation_${TIMESTAMP}.log"

# Email configuration (from .env)
EMAIL_ENABLED="${EMAIL_ENABLED:-false}"
EMAIL_RECIPIENTS="${EMAIL_RECIPIENTS:-admin@example.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "${LOG_FILE}"
}

# Create necessary directories
mkdir -p "${LOG_DIR}"
mkdir -p "${REPORT_DIR}"

log "========================================="
log "Weekly Validation Job Started"
log "========================================="
log "Project Directory: ${PROJECT_DIR}"
log "Log File: ${LOG_FILE}"

# Change to project directory
cd "${PROJECT_DIR}"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    log "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    log "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run validation for each horizon
HORIZONS=("7d" "15d" "30d" "90d")
ALL_SUCCESS=true

for horizon in "${HORIZONS[@]}"; do
    log "-------------------------------------------"
    log "Running validation for horizon: ${horizon}"
    log "-------------------------------------------"

    # Run validation script
    if python scripts/validate_model.py \
        --horizon "${horizon}" \
        --mode rolling \
        --folds 3 \
        --output "${REPORT_DIR}/validation_${horizon}_${TIMESTAMP}.json" \
        >> "${LOG_FILE}" 2>&1; then

        log_success "Validation completed for ${horizon}"
    else
        log_error "Validation failed for ${horizon}"
        ALL_SUCCESS=false
    fi
done

# Check performance degradation
log "-------------------------------------------"
log "Checking Performance Degradation"
log "-------------------------------------------"

if python scripts/check_performance.py --all >> "${LOG_FILE}" 2>&1; then
    log_success "Performance check completed"
else
    log_warning "Performance check failed or degradation detected"
fi

# Generate summary report
log "-------------------------------------------"
log "Generating Summary Report"
log "-------------------------------------------"

SUMMARY_FILE="${REPORT_DIR}/weekly_summary_${TIMESTAMP}.txt"

cat > "${SUMMARY_FILE}" <<EOF
===========================================
Weekly Validation Summary
===========================================
Date: $(date +'%Y-%m-%d %H:%M:%S')
Project: USD/CLP Forecasting System

Validation Results:
EOF

# Add validation results for each horizon
for horizon in "${HORIZONS[@]}"; do
    latest_report="${REPORT_DIR}/validation_${horizon}_${TIMESTAMP}.json"
    if [ -f "${latest_report}" ]; then
        echo "  - ${horizon}: ✓ Completed" >> "${SUMMARY_FILE}"
    else
        echo "  - ${horizon}: ✗ Failed" >> "${SUMMARY_FILE}"
    fi
done

# Add performance status
echo "" >> "${SUMMARY_FILE}"
echo "Performance Status:" >> "${SUMMARY_FILE}"
python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from forex_core.mlops.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor(data_dir=Path('data'))
reports = monitor.check_all_horizons()

for horizon, report in reports.items():
    status = report.status.value.upper()
    degraded = '⚠ DEGRADED' if report.degradation_detected else '✓ OK'
    print(f'  - {horizon}: {status} ({degraded})')
" >> "${SUMMARY_FILE}" 2>&1 || echo "  - Unable to fetch performance status" >> "${SUMMARY_FILE}"

# Add log location
cat >> "${SUMMARY_FILE}" <<EOF

Detailed Logs:
  ${LOG_FILE}

Reports Directory:
  ${REPORT_DIR}

===========================================
EOF

log_success "Summary report generated: ${SUMMARY_FILE}"

# Display summary
cat "${SUMMARY_FILE}"

# Send email if configured
if [ "${EMAIL_ENABLED}" = "true" ]; then
    log "Sending email notification to ${EMAIL_RECIPIENTS}..."

    if python -c "
import sys
sys.path.insert(0, 'src')
from forex_core.notifications.email_sender import EmailSender

sender = EmailSender()
with open('${SUMMARY_FILE}') as f:
    body = f.read()

sender.send_email(
    subject='Weekly Validation Report - $(date +%Y-%m-%d)',
    body=body,
)
" >> "${LOG_FILE}" 2>&1; then
        log_success "Email sent successfully"
    else
        log_warning "Failed to send email notification"
    fi
else
    log "Email notifications disabled (EMAIL_ENABLED=${EMAIL_ENABLED})"
fi

# Cleanup old logs (keep last 30 days)
log "Cleaning up old logs..."
find "${LOG_DIR}" -name "weekly_validation_*.log" -mtime +30 -delete 2>/dev/null || true
find "${REPORT_DIR}" -name "validation_*.json" -mtime +90 -delete 2>/dev/null || true
find "${REPORT_DIR}" -name "weekly_summary_*.txt" -mtime +90 -delete 2>/dev/null || true

# Final status
log "========================================="
if [ "${ALL_SUCCESS}" = true ]; then
    log_success "Weekly validation completed successfully"
    exit 0
else
    log_error "Weekly validation completed with errors"
    exit 1
fi
