#!/usr/bin/env bash
set -e

echo "🚀 Starting USD/CLP 15-Day Forecaster Service"
echo "=============================================="

# Load environment variables from .env file
if [ -f "/app/.env" ]; then
    set -o allexport
    source /app/.env || echo "Warning: Failed to source .env"
    set +o allexport
    echo "✓ Environment variables loaded"
fi

# Create log file
touch /var/log/cron.log
echo "✓ Log file created at /var/log/cron.log"

# Export all environment variables for cron
printenv | grep -v "^_" | grep -v "^HOME=" | grep -v "^PWD=" > /etc/environment
echo "✓ Environment exported to /etc/environment"

# Install crontab
crontab /etc/cron.d/usdclp-15d
echo "✓ Crontab installed"

# Verify crontab
echo ""
echo "Loaded crontab:"
crontab -l
echo ""

# Start cron in foreground
echo "✓ Starting cron daemon..."
echo "✓ Logs available at /var/log/cron.log"
echo "=============================================="

cron && tail -f /var/log/cron.log
