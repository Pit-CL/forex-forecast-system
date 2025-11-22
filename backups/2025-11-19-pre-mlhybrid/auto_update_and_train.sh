#\!/bin/bash
# Automatic Data Update and Model Training Script
# This script updates Yahoo Finance data and retrains models daily

set -e  # Exit on error

LOG_FILE="/opt/forex-forecast-system/logs/auto_update_$(date +%Y%m%d).log"
mkdir -p /opt/forex-forecast-system/logs

echo "=========================================" | tee -a "$LOG_FILE"
echo "Auto Update Started: $(date)" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

# Change to project directory
cd /opt/forex-forecast-system

# Activate virtual environment
echo "🔧 Activating virtual environment..." | tee -a "$LOG_FILE"
source /opt/forex-forecast-system/venv/bin/activate

# Step 1: Collect new data from Yahoo Finance
echo "" | tee -a "$LOG_FILE"
echo "📥 Step 1: Collecting data from Yahoo Finance..." | tee -a "$LOG_FILE"
if python3 scripts/collect_data.py >> "$LOG_FILE" 2>&1; then
    echo "✅ Data collection successful" | tee -a "$LOG_FILE"
else
    echo "❌ Data collection failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2: Retrain models with new data
echo "" | tee -a "$LOG_FILE"
echo "🤖 Step 2: Retraining models with updated data..." | tee -a "$LOG_FILE"
if python3 scripts/train_models_v3_optimized.py >> "$LOG_FILE" 2>&1; then
    echo "✅ Model training successful" | tee -a "$LOG_FILE"
else
    echo "❌ Model training failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Restart API to load new models
echo "" | tee -a "$LOG_FILE"
echo "🔄 Step 3: Restarting API..." | tee -a "$LOG_FILE"
if cd /opt/forex-forecast-system && docker compose -f docker-compose-simple.yml restart api >> "$LOG_FILE" 2>&1; then
    echo "✅ API restarted successfully" | tee -a "$LOG_FILE"
else
    echo "❌ API restart failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
echo "Auto Update Completed: $(date)" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

# Keep only last 30 days of logs
find /opt/forex-forecast-system/logs -name "auto_update_*.log" -mtime +30 -delete

# Deactivate virtual environment
deactivate
