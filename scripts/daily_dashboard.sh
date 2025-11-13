#!/bin/bash
###############################################################################
# Daily Dashboard Report Script
#
# Generates and emails daily system status dashboard.
# Designed to run via cron job every day at 8 AM.
#
# Cron entry:
# 0 8 * * * cd /path/to/forex-forecast-system && ./scripts/daily_dashboard.sh
###############################################################################

set -e
set -u

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
REPORT_DIR="${PROJECT_DIR}/reports/daily"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DATE_TODAY=$(date +%Y-%m-%d)
LOG_FILE="${LOG_DIR}/daily_dashboard_${TIMESTAMP}.log"

# Email configuration
EMAIL_ENABLED="${EMAIL_ENABLED:-false}"
EMAIL_RECIPIENTS="${EMAIL_RECIPIENTS:-admin@example.com}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

# Create directories
mkdir -p "${LOG_DIR}"
mkdir -p "${REPORT_DIR}"

log "========================================="
log "Daily Dashboard Report - ${DATE_TODAY}"
log "========================================="

cd "${PROJECT_DIR}"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Generate HTML dashboard
HTML_REPORT="${REPORT_DIR}/dashboard_${DATE_TODAY}.html"

log "Generating HTML dashboard..."

python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from forex_core.mlops.performance_monitor import PerformanceMonitor
from forex_core.mlops.readiness import ChronosReadinessChecker

# Initialize
data_dir = Path('data')
monitor = PerformanceMonitor(data_dir=data_dir)
readiness_checker = ChronosReadinessChecker(data_dir=data_dir)

# Collect data
perf_reports = monitor.check_all_horizons()
readiness_report = readiness_checker.assess()

# Load recent predictions
predictions_path = data_dir / 'predictions' / 'predictions.parquet'
if predictions_path.exists():
    df = pd.read_parquet(predictions_path)
    recent_cutoff = datetime.now() - timedelta(days=7)
    recent_df = df[df['forecast_date'] > pd.Timestamp(recent_cutoff)]
else:
    recent_df = pd.DataFrame()

# Generate HTML
html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Forex Forecasting Dashboard - {datetime.now().strftime(\"%Y-%m-%d\")}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header .date {{
            margin-top: 5px;
            opacity: 0.9;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        .status-excellent {{ color: #28a745; font-weight: bold; }}
        .status-good {{ color: #28a745; }}
        .status-degraded {{ color: #ffc107; font-weight: bold; }}
        .status-critical {{ color: #dc3545; font-weight: bold; }}
        .metric-positive {{ color: #28a745; }}
        .metric-negative {{ color: #dc3545; }}
        .readiness-optimal {{ color: #28a745; font-weight: bold; }}
        .readiness-ready {{ color: #17a2b8; font-weight: bold; }}
        .readiness-cautious {{ color: #ffc107; font-weight: bold; }}
        .readiness-not-ready {{ color: #dc3545; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>USD/CLP Forecasting System Dashboard</h1>
        <div class=\"date\">{datetime.now().strftime(\"%A, %B %d, %Y %H:%M\")}</div>
    </div>

    <!-- System Status -->
    <div class=\"card\">
        <h2>📊 System Status</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Recent Predictions (7 days)</td>
                <td>{len(recent_df)}</td>
            </tr>
            <tr>
                <td>Chronos Readiness</td>
                <td class=\"readiness-{readiness_report.level.value}\">{readiness_report.level.value.upper()} ({readiness_report.score:.0f}/100)</td>
            </tr>
        </table>
    </div>

    <!-- Performance Status -->
    <div class=\"card\">
        <h2>🎯 Performance Status</h2>
        <table>
            <tr>
                <th>Horizon</th>
                <th>Status</th>
                <th>RMSE Change</th>
                <th>MAPE Change</th>
                <th>Samples</th>
            </tr>
'''

for horizon in ['7d', '15d', '30d', '90d']:
    report = perf_reports[horizon]
    status_class = f\"status-{report.status.value}\"
    rmse_delta = report.degradation_pct.get('rmse', 0.0)
    mape_delta = report.degradation_pct.get('mape', 0.0)
    rmse_class = 'metric-negative' if rmse_delta > 0 else 'metric-positive'
    mape_class = 'metric-negative' if mape_delta > 0 else 'metric-positive'

    html += f'''
            <tr>
                <td>{horizon}</td>
                <td class=\"{status_class}\">{report.status.value.upper()}</td>
                <td class=\"{rmse_class}\">{rmse_delta:+.1f}%</td>
                <td class=\"{mape_class}\">{mape_delta:+.1f}%</td>
                <td>{report.recent_metrics.n_predictions}</td>
            </tr>
'''

html += '''
        </table>
    </div>

    <!-- Readiness Checks -->
    <div class=\"card\">
        <h2>✅ Readiness Checks</h2>
        <table>
            <tr>
                <th>Check</th>
                <th>Status</th>
                <th>Score</th>
                <th>Message</th>
            </tr>
'''

for check in readiness_report.checks:
    status_icon = '✓' if check.passed else '✗'
    status_class = 'metric-positive' if check.passed else 'metric-negative'

    html += f'''
            <tr>
                <td>{check.check_name}</td>
                <td class=\"{status_class}\">{status_icon}</td>
                <td>{check.score:.0f}/100</td>
                <td style=\"font-size: 0.9em;\">{check.message}</td>
            </tr>
'''

html += f'''
        </table>
    </div>

    <!-- Recommendations -->
    <div class=\"card\">
        <h2>💡 Recommendations</h2>
        <p><strong>Readiness:</strong> {readiness_report.recommendation}</p>
'''

# Add performance recommendations if degraded
for horizon, report in perf_reports.items():
    if report.degradation_detected:
        html += f'<p><strong>{horizon}:</strong> {report.recommendation}</p>'

html += '''
    </div>

    <div class=\"footer\">
        Generated by USD/CLP Forecasting System | Automated Daily Report
    </div>
</body>
</html>
'''

# Write HTML
with open('${HTML_REPORT}', 'w') as f:
    f.write(html)

print('HTML dashboard generated successfully')
" >> "${LOG_FILE}" 2>&1

if [ $? -eq 0 ]; then
    log_success "HTML dashboard generated: ${HTML_REPORT}"
else
    log_error "Failed to generate HTML dashboard"
    exit 1
fi

# Send email if configured
if [ "${EMAIL_ENABLED}" = "true" ]; then
    log "Sending email with HTML dashboard..."

    python -c "
import sys
sys.path.insert(0, 'src')
from forex_core.notifications.email_sender import EmailSender

sender = EmailSender()

# Read HTML
with open('${HTML_REPORT}') as f:
    html_content = f.read()

# Send email
sender.send_html_email(
    subject='Daily Dashboard - USD/CLP Forecasting System - $(date +%Y-%m-%d)',
    html_body=html_content,
)
" >> "${LOG_FILE}" 2>&1

    if [ $? -eq 0 ]; then
        log_success "Email sent successfully to ${EMAIL_RECIPIENTS}"
    else
        log_error "Failed to send email"
    fi
else
    log "Email disabled. HTML report saved to: ${HTML_REPORT}"
fi

# Cleanup old reports (keep last 30 days)
find "${REPORT_DIR}" -name "dashboard_*.html" -mtime +30 -delete 2>/dev/null || true

log "========================================="
log_success "Daily dashboard completed"
log "========================================="
