#!/usr/bin/env bash
# Automated 7-day forecast runner for cron

set -e

# Paths
PROJECT_DIR="/home/deployer/forex-forecast-system"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
REPORT_DIR="$PROJECT_DIR/reports"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# Logging
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/forecast_7d_$TIMESTAMP.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "7-Day Forecast Run: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set Python path
export PYTHONPATH="$PROJECT_DIR/src"

# Run forecast using fixed pipeline
cd "$PROJECT_DIR"
python3 << PYTHON_EOF 2>&1 | tee -a "$LOG_FILE"
import sys
sys.path.insert(0, "/home/deployer/forex-forecast-system/src")

from pathlib import Path
from dataclasses import asdict
from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.forecasting import ForecastEngine
from forex_core.reporting import ChartGenerator, ReportBuilder

print("🚀 Iniciando generación automática de pronóstico 7 días...")

# Load data
print("📊 Cargando datos...")
settings = get_settings()
loader = DataLoader(settings)
bundle = loader.load()
print(f"✓ Datos cargados: {len(bundle.indicators)} indicadores")

# Generate forecast
print("🔮 Generando pronóstico...")
engine = ForecastEngine(settings)
forecast, artifacts = engine.forecast(bundle)
print(f"✓ Pronóstico generado: {len(forecast.series)} puntos")

# Generate charts
print("📈 Generando gráficos...")
chart_gen = ChartGenerator(settings)
charts = chart_gen.generate(bundle, forecast, horizon="7d")
print(f"✓ Gráficos: {len(charts)}")

# Build PDF
print("📄 Generando PDF...")
builder = ReportBuilder(settings)
artifacts_dict = asdict(artifacts)
pdf_path = builder.build(bundle, forecast, artifacts_dict, charts, horizon="7d")
print(f"✅ PDF generado: {pdf_path}")
print(f"📁 Tamaño: {pdf_path.stat().st_size / 1024:.1f} KB")
PYTHON_EOF

EXIT_CODE=$?

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Forecast completado exitosamente" | tee -a "$LOG_FILE"
else
    echo "❌ Forecast falló con código: $EXIT_CODE" | tee -a "$LOG_FILE"
fi
echo "Log guardado en: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
