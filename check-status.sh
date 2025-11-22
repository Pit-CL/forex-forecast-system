#!/bin/bash
echo "=== Forex Forecast System Status ==="
echo ""

echo "🔷 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E 'NAMES|forex'
echo ""

echo "🔷 API Health:"
HEALTH=$(curl -s http://localhost:8000/api/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$HEALTH" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'  Status: {data[\"status\"]}'); print(f'  Version: {data[\"version\"]}'); print(f'  Uptime: {int(data[\"uptime_seconds\"])}s')" 2>/dev/null || echo "  API responding but parse error"
else
    echo "  ❌ API not responding"
fi
echo ""

echo "🔷 Current USD/CLP Rate:"
FORECASTS=$(curl -s http://localhost:8000/api/forecasts 2>/dev/null)
if [ $? -eq 0 ]; then
    CURRENT=$(echo "$FORECASTS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'\${data[\"current_price\"]:.2f}')" 2>/dev/null)
    echo "  ${CURRENT:-N/A}"
else
    echo "  ❌ Cannot fetch"
fi
echo ""

echo "🔷 Forecast Summary (from JSON files):"
python3 << 'PYEOF'
import json
from pathlib import Path

forecasts_dir = Path('/opt/forex-forecast-system/output/forecasts')
for horizon in ['7d', '15d', '30d', '90d']:
    json_file = forecasts_dir / f'forecast_{horizon}.json'
    if json_file.exists():
        try:
            with open(json_file) as f:
                data = json.load(f)
                model = data.get('model_type', 'Unknown')
                target = data['target']
                mape = data['metadata'].get('mape', 0)
                change = target['change_percent']
                arrow = '↑' if change > 0 else '↓'
                print(f"  {horizon.upper()}: ${target['price']:.2f} ({arrow}{abs(change):.2f}%) - {model} MAPE:{mape:.2f}%")
        except Exception as e:
            print(f"  {horizon.upper()}: ❌ Error reading JSON")
    else:
        print(f"  {horizon.upper()}: ❌ JSON not found")
PYEOF
echo ""

echo "🔷 Last Model Training:"
ls -lh /opt/forex-forecast-system/models/trained/7D/elasticnet_backup.joblib 2>/dev/null | awk '{print "  "$6" "$7" "$8" - ElasticNet"}'
ls -lh /opt/forex-forecast-system/models/trained/7D/lightgbm_primary.joblib 2>/dev/null | awk '{print "  "$6" "$7" "$8" - LightGBM"}'
echo ""

echo "🔷 Last Forecast Generation:"
ls -lh /opt/forex-forecast-system/output/forecasts/forecast_7d.json 2>/dev/null | awk '{print "  "$6" "$7" "$8}'
echo ""

echo "🔷 Access URLs:"
echo "  Frontend: http://155.138.162.47/"
echo "  API: http://155.138.162.47/api/"
echo "  Health: http://155.138.162.47/api/health"
echo "  Docs: http://155.138.162.47/api/docs"
echo ""

echo "🔷 Recent CRON Execution:"
LATEST_LOG=$(ls -t /opt/forex-forecast-system/logs/auto_update_*.log 2>/dev/null | head -1)
if [ -f "$LATEST_LOG" ]; then
    echo "  Log: $(basename $LATEST_LOG)"
    tail -3 "$LATEST_LOG" | grep -E "Completed|successful|failed" | head -1 | sed 's/^/  /'
else
    echo "  No logs found"
fi
