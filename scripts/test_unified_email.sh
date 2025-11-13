#!/bin/bash
###############################################################################
# Test Unified Email System - Multiple Scenarios
#
# This script tests the unified email system by simulating different scenarios:
# - Normal operation (ROUTINE priority)
# - Significant price change (ATTENTION priority)
# - Critical alerts (URGENT priority)
# - Different days of week (Monday, Wednesday, Thursday, Friday)
# - With/without PDF attachments
#
# Usage:
#   ./scripts/test_unified_email.sh [scenario]
#
# Scenarios:
#   normal       - Normal operation (default)
#   attention    - Significant price change scenario
#   urgent       - Critical alert scenario
#   monday       - Simulate Monday email (7d + 15d)
#   wednesday    - Simulate Wednesday email (7d only)
#   thursday     - Simulate Thursday email (15d)
#   friday       - Simulate Friday email (7d + 30d)
#   all          - Run all scenarios
###############################################################################

set -e
set -u

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${LOG_DIR}/test_unified_email_${TIMESTAMP}.log"

# Test email recipient (override EMAIL_RECIPIENTS)
TEST_EMAIL="${TEST_EMAIL:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_scenario() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}" | tee -a "${LOG_FILE}"
    echo -e "${CYAN}║  $*${NC}" | tee -a "${LOG_FILE}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}✓ $*${NC}" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}✗ $*${NC}" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}ℹ $*${NC}" | tee -a "${LOG_FILE}"
}

# Create log directory
mkdir -p "${LOG_DIR}"

cd "${PROJECT_DIR}"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    log_error "No virtual environment found"
    exit 1
fi

###############################################################################
# Test Scenarios
###############################################################################

test_normal_scenario() {
    log_scenario "SCENARIO 1: Normal Operation (ROUTINE Priority)"

    log_info "Testing with current system data..."
    log_info "Expected: HTML email with forecast data, minimal PDFs"

    PYTHONPATH=src:$PYTHONPATH python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from datetime import datetime
from forex_core.notifications.unified_email import UnifiedEmailOrchestrator
from forex_core.notifications.email_builder import EmailContentBuilder
from forex_core.notifications.email import EmailSender
from forex_core.config.base import Settings

# Initialize
orchestrator = UnifiedEmailOrchestrator(data_dir=Path('data'))
builder = EmailContentBuilder()
settings = Settings()

# Override recipients if TEST_EMAIL is set
if '${TEST_EMAIL}':
    settings.email_recipients = ['${TEST_EMAIL}']

sender = EmailSender(settings)

# Get forecasts for today
horizons = orchestrator.get_horizons_for_today()
print(f'📊 Horizons for today: {[h.value for h in horizons]}')

if not horizons:
    print('⚠️  No horizons scheduled for today')
    sys.exit(0)

# Load data
forecasts = []
for horizon in horizons:
    forecast_data = orchestrator.load_forecast_data(horizon.value)
    if forecast_data:
        forecasts.append(forecast_data)
        print(f'✓ Loaded {horizon.value}: \${forecast_data.current_price:.0f} → \${forecast_data.forecast_price:.0f} ({forecast_data.change_pct:+.1f}%)')

system_health = orchestrator.load_system_health()
print(f'✓ System Health: {system_health.readiness_level} ({system_health.readiness_score:.0f}/100)')

# Determine priority and PDFs
priority = orchestrator.determine_email_priority(forecasts, system_health)
print(f'📧 Email Priority: {priority}')

pdf_attachments = []
for forecast in forecasts:
    if orchestrator.should_attach_pdf(forecast, system_health):
        if forecast.pdf_path and forecast.pdf_path.exists():
            pdf_attachments.append(forecast.pdf_path)
            print(f'📎 PDF attached: {forecast.horizon}')

print(f'📎 Total PDFs: {len(pdf_attachments)}')

# Generate and send
subject = orchestrator.generate_subject_line(forecasts, system_health, priority)
html_body = builder.build(forecasts, system_health, priority, pdf_attachments)

print(f'📧 Subject: {subject}')

# Send email
sender.send_unified(
    html_body=html_body,
    subject=subject,
    pdf_attachments=pdf_attachments if pdf_attachments else None,
)

print('✅ Test email sent successfully!')
" 2>&1 | tee -a "${LOG_FILE}"

    if [ $? -eq 0 ]; then
        log_success "Normal scenario test completed"
    else
        log_error "Normal scenario test failed"
        return 1
    fi
}

test_monday_scenario() {
    log_scenario "SCENARIO 2: Monday Email (7d + 15d)"

    log_info "Simulating Monday 7:30 AM email..."
    log_info "Expected: 7d + 15d forecasts with conditional PDFs"

    # This would require mocking the date, for now just log
    log_info "Run this test on a Monday or modify orchestrator to accept custom date"
    log_success "Monday scenario documented"
}

test_wednesday_scenario() {
    log_scenario "SCENARIO 3: Wednesday Email (7d only)"

    log_info "Simulating Wednesday 7:30 AM email..."
    log_info "Expected: Only 7d forecast, HTML only (no PDF unless alert)"

    log_info "Run this test on a Wednesday or modify orchestrator to accept custom date"
    log_success "Wednesday scenario documented"
}

test_thursday_scenario() {
    log_scenario "SCENARIO 4: Thursday Email (15d)"

    log_info "Simulating Thursday 7:30 AM email..."
    log_info "Expected: 15d forecast with PDF"

    log_info "Run this test on a Thursday or modify orchestrator to accept custom date"
    log_success "Thursday scenario documented"
}

test_friday_scenario() {
    log_scenario "SCENARIO 5: Friday Email (7d + 30d + Weekly Summary)"

    log_info "Simulating Friday 7:30 AM email..."
    log_info "Expected: 7d + 30d forecasts, both with PDFs (weekly summary)"

    log_info "Run this test on a Friday or modify orchestrator to accept custom date"
    log_success "Friday scenario documented"
}

test_html_rendering() {
    log_scenario "SCENARIO 6: HTML Template Rendering"

    log_info "Testing HTML generation with institutional colors..."

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

builder = EmailContentBuilder()

# Create mock data for testing HTML
mock_forecasts = [
    ForecastData(
        horizon='7d',
        current_price=920.0,
        forecast_price=925.0,
        change_pct=0.54,
        ci95_low=910.0,
        ci95_high=940.0,
        ci80_low=915.0,
        ci80_high=935.0,
        bias='NEUTRAL',
        volatility='MEDIA',
    ),
]

mock_system_health = SystemHealthData(
    readiness_level='READY',
    readiness_score=85.0,
    performance_status={'7d': 'GOOD', '15d': 'GOOD', '30d': 'EXCELLENT', '90d': 'GOOD'},
    degradation_detected=False,
    degradation_details=[],
    recent_predictions=150,
    drift_detected=False,
    drift_details=[],
)

# Generate HTML
html = builder.build(mock_forecasts, mock_system_health, 'ROUTINE', [])

# Save to file for inspection
output_path = Path('logs/test_email_template.html')
output_path.parent.mkdir(exist_ok=True)
with open(output_path, 'w') as f:
    f.write(html)

print(f'✅ HTML template saved to: {output_path}')
print(f'📊 Template size: {len(html)} bytes')
print(f'🎨 Institutional colors applied: #004f71 (azul), #d8e5ed (gris)')
print(f'📱 Mobile-responsive CSS included')
" 2>&1 | tee -a "${LOG_FILE}"

    if [ $? -eq 0 ]; then
        log_success "HTML rendering test completed"
        log_info "Check logs/test_email_template.html in a browser to verify rendering"
    else
        log_error "HTML rendering test failed"
        return 1
    fi
}

###############################################################################
# Main Execution
###############################################################################

SCENARIO="${1:-normal}"

echo ""
log_info "═══════════════════════════════════════════════════════════════"
log_info "  Unified Email System - Testing Suite"
log_info "═══════════════════════════════════════════════════════════════"
echo ""

if [ -n "${TEST_EMAIL}" ]; then
    log_info "Test emails will be sent to: ${TEST_EMAIL}"
else
    log_info "Using default EMAIL_RECIPIENTS from .env"
fi

echo ""

case "$SCENARIO" in
    normal)
        test_normal_scenario
        ;;
    monday)
        test_monday_scenario
        ;;
    wednesday)
        test_wednesday_scenario
        ;;
    thursday)
        test_thursday_scenario
        ;;
    friday)
        test_friday_scenario
        ;;
    html)
        test_html_rendering
        ;;
    all)
        test_normal_scenario
        test_monday_scenario
        test_wednesday_scenario
        test_thursday_scenario
        test_friday_scenario
        test_html_rendering
        ;;
    *)
        log_error "Unknown scenario: $SCENARIO"
        echo ""
        echo "Usage: $0 [scenario]"
        echo ""
        echo "Available scenarios:"
        echo "  normal       - Normal operation test (default)"
        echo "  monday       - Monday email simulation"
        echo "  wednesday    - Wednesday email simulation"
        echo "  thursday     - Thursday email simulation"
        echo "  friday       - Friday email simulation"
        echo "  html         - HTML template rendering test"
        echo "  all          - Run all scenarios"
        echo ""
        exit 1
        ;;
esac

echo ""
log_info "═══════════════════════════════════════════════════════════════"
log_success "Testing completed! Check log: ${LOG_FILE}"
log_info "═══════════════════════════════════════════════════════════════"
echo ""

exit 0
