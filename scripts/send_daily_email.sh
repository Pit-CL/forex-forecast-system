#!/bin/bash
###############################################################################
# Unified Daily Email Script
#
# Sends intelligent unified emails based on market-optimized strategy.
# Replaces daily_dashboard.sh with smarter, consolidated approach.
#
# Strategy:
# - Monday 7:30 AM: 7d + 15d forecasts
# - Wednesday 7:30 AM: 7d forecast only
# - Thursday 7:30 AM: 15d forecast
# - Friday 7:30 AM: 7d + 30d + weekly summary
#
# Cron entry:
# 30 7 * * 1,3,4,5 cd /path/to/forex-forecast-system && ./scripts/send_daily_email.sh
###############################################################################

set -e
set -u

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DATE_TODAY=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
LOG_FILE="${LOG_DIR}/unified_email_${TIMESTAMP}.log"

# Email configuration
EMAIL_ENABLED="${EMAIL_ENABLED:-true}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "${LOG_FILE}"
}

# Create log directory
mkdir -p "${LOG_DIR}"

log "========================================="
log "Unified Daily Email - ${DATE_TODAY}"
log "Day of Week: ${DAY_OF_WEEK} (1=Mon, 7=Sun)"
log "========================================="

cd "${PROJECT_DIR}"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    log_info "Activated venv"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    log_info "Activated .venv"
else
    log_error "No virtual environment found"
    exit 1
fi

# Check if email should be sent today
log_info "Checking if email should be sent today..."

SHOULD_SEND=$(PYTHONPATH=src:$PYTHONPATH python -c "
from pathlib import Path
from datetime import datetime
from forex_core.notifications.unified_email import UnifiedEmailOrchestrator

orchestrator = UnifiedEmailOrchestrator(data_dir=Path('data'))
should_send = orchestrator.should_send_email_today()
print('true' if should_send else 'false')
" 2>>"${LOG_FILE}")

if [ "$SHOULD_SEND" != "true" ]; then
    log_info "No email scheduled for today. Exiting."
    exit 0
fi

log_success "Email should be sent today"

# Get horizons to include
log_info "Determining which horizons to include..."

HORIZONS=$(PYTHONPATH=src:$PYTHONPATH python -c "
from pathlib import Path
from forex_core.notifications.unified_email import UnifiedEmailOrchestrator

orchestrator = UnifiedEmailOrchestrator(data_dir=Path('data'))
horizons = orchestrator.get_horizons_for_today()
print(','.join([h.value for h in horizons]))
" 2>>"${LOG_FILE}")

log_info "Horizons for today: ${HORIZONS}"

# Generate and send unified email
log_info "Generating unified email..."

PYTHONPATH=src:$PYTHONPATH python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from datetime import datetime
from forex_core.notifications.unified_email import (
    UnifiedEmailOrchestrator,
    ForecastData,
    SystemHealthData,
)
from forex_core.notifications.email_builder import EmailContentBuilder
from forex_core.notifications.email import EmailSender
from forex_core.config.base import Settings

# Initialize components
data_dir = Path('data')
orchestrator = UnifiedEmailOrchestrator(data_dir=data_dir)
builder = EmailContentBuilder()
settings = Settings()
sender = EmailSender(settings)

# Get horizons for today
horizons = orchestrator.get_horizons_for_today()

if not horizons:
    print('No horizons to send today')
    sys.exit(0)

print(f'Processing {len(horizons)} horizons: {[h.value for h in horizons]}')

# Load forecast data for each horizon
forecasts = []
for horizon in horizons:
    forecast_data = orchestrator.load_forecast_data(horizon.value)
    if forecast_data:
        forecasts.append(forecast_data)
    else:
        print(f'Warning: No forecast data available for {horizon.value}')

# Load system health
system_health = orchestrator.load_system_health()

# Determine priority
priority = orchestrator.determine_email_priority(forecasts, system_health)
print(f'Email priority: {priority}')

# Determine which PDFs to attach
pdf_attachments = []
for forecast in forecasts:
    if orchestrator.should_attach_pdf(forecast, system_health):
        if forecast.pdf_path and forecast.pdf_path.exists():
            pdf_attachments.append(forecast.pdf_path)
            print(f'Will attach PDF for {forecast.horizon}')
        else:
            print(f'Warning: PDF not found for {forecast.horizon}')

print(f'Total PDF attachments: {len(pdf_attachments)}')

# Generate subject line
subject = orchestrator.generate_subject_line(forecasts, system_health, priority)
print(f'Subject: {subject}')

# Build HTML content
html_body = builder.build(
    forecasts=forecasts,
    system_health=system_health,
    priority=priority,
    pdf_attachments=pdf_attachments,
)

# Send unified email
sender.send_unified(
    html_body=html_body,
    subject=subject,
    pdf_attachments=pdf_attachments if pdf_attachments else None,
)

print(f'✅ Unified email sent successfully')
print(f'   - Horizons: {[f.horizon for f in forecasts]}')
print(f'   - PDFs attached: {len(pdf_attachments)}')
print(f'   - Priority: {priority}')

" >> "${LOG_FILE}" 2>&1

if [ $? -eq 0 ]; then
    log_success "Unified email sent successfully"
else
    log_error "Failed to send unified email"
    exit 1
fi

# Cleanup old logs (keep last 30 days)
find "${LOG_DIR}" -name "unified_email_*.log" -mtime +30 -delete 2>/dev/null || true

log "========================================="
log_success "Unified email process completed"
log "========================================="

exit 0
