#!/bin/bash
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

# Step 2: Retrain LightGBM models with new data
echo "" | tee -a "$LOG_FILE"
echo "🤖 Step 2a: Retraining LightGBM models..." | tee -a "$LOG_FILE"
if python3 scripts/train_models_v3_optimized.py >> "$LOG_FILE" 2>&1; then
    echo "✅ LightGBM training successful" | tee -a "$LOG_FILE"
else
    echo "❌ LightGBM training failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2b: Retrain ElasticNet models
echo "" | tee -a "$LOG_FILE"
echo "🔄 Step 2b: Retraining ElasticNet models..." | tee -a "$LOG_FILE"
if python3 scripts/retrain_elasticnet.py >> "$LOG_FILE" 2>&1; then
    echo "✅ ElasticNet training successful" | tee -a "$LOG_FILE"
else
    echo "❌ ElasticNet training failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2b.5: Archive existing forecasts for backtesting
echo "" | tee -a "$LOG_FILE"
echo "📦 Step 2b.5: Archiving existing forecasts for backtesting..." | tee -a "$LOG_FILE"
ARCHIVE_DIR="/opt/forex-forecast-system/backtest/archive"
FORECAST_DIR="/opt/forex-forecast-system/output/forecasts"
TIMESTAMP=$(date +%Y-%m-%d)

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"

# Archive each forecast with timestamp
for horizon in 7d 15d 30d 90d; do
    FORECAST_FILE="$FORECAST_DIR/forecast_${horizon}.json"
    if [ -f "$FORECAST_FILE" ]; then
        ARCHIVE_FILE="$ARCHIVE_DIR/${TIMESTAMP}_${horizon}_forecast.json"
        cp "$FORECAST_FILE" "$ARCHIVE_FILE"
        echo "  ✓ Archived ${horizon} forecast" | tee -a "$LOG_FILE"
    fi
done

echo "✅ Forecast archiving successful" | tee -a "$LOG_FILE"

# Step 2c: Generate forecast JSON files
echo "" | tee -a "$LOG_FILE"
echo "📊 Step 2c: Generating forecast JSON files..." | tee -a "$LOG_FILE"
if python3 scripts/generate_real_forecasts.py --all >> "$LOG_FILE" 2>&1; then
    echo "✅ Forecast generation successful" | tee -a "$LOG_FILE"
else
    echo "❌ Forecast generation failed" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 2d: Run backtesting on archived forecasts
echo "" | tee -a "$LOG_FILE"
echo "📊 Step 2d: Running backtesting on historical forecasts..." | tee -a "$LOG_FILE"
if python3 scripts/backtest_forecasts.py >> "$LOG_FILE" 2>&1; then
    echo "✅ Backtesting successful" | tee -a "$LOG_FILE"
else
    echo "⚠️  Backtesting failed (non-critical)" | tee -a "$LOG_FILE"
    # Don't exit on backtesting failure - it's not critical

# Step 2e: Run historical backtesting (walk-forward validation)
echo "" | tee -a "$LOG_FILE"
echo "📊 Step 2e: Running historical backtesting (walk-forward validation)..." | tee -a "$LOG_FILE"
if python3 scripts/backtest_historical.py >> "$LOG_FILE" 2>&1; then
    echo "✅ Historical backtesting successful" | tee -a "$LOG_FILE"
else
    echo "⚠️  Historical backtesting failed (non-critical)" | tee -a "$LOG_FILE"
    # Don't exit on backtesting failure - it's not critical
fi
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

# Keep only last 90 days of archived forecasts
find /opt/forex-forecast-system/backtest/archive -name "*_forecast.json" -mtime +90 -delete

# Deactivate virtual environment
deactivate
