#!/usr/bin/env python3
"""Script rápido para generar PDF con el sistema completo"""

import sys
sys.path.insert(0, '/home/deployer/forex-forecast-system/src')

from pathlib import Path
from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.forecasting import ForecastEngine
from forex_core.reporting import ChartGenerator, ReportBuilder

print('🚀 Iniciando generación de PDF completo...')

# 1. Cargar datos
print('📊 Cargando datos...')
settings = get_settings()
loader = DataLoader(settings)
bundle = loader.load()
print(f'✓ Datos cargados: {len(bundle.indicators)} indicadores')

# 2. Generar forecast
print('🔮 Generando pronóstico 7 días...')
engine = ForecastEngine(settings)
forecast = engine.forecast(bundle, days=7)
print(f'✓ Pronóstico generado: {len(forecast.series)} puntos')

# 3. Generar gráficos
print('📈 Generando gráficos...')
chart_gen = ChartGenerator(settings)
charts = chart_gen.generate(bundle, forecast, horizon='7d')
print(f'✓ Gráficos generados: {len(charts)}')

# 4. Generar PDF
print('📄 Generando PDF...')
builder = ReportBuilder(settings)
artifacts = {'weights': {'arima': 0.4, 'var': 0.3, 'rf': 0.3}}
pdf_path = builder.build(bundle, forecast, artifacts, charts, horizon='7d')
print(f'✅ PDF generado: {pdf_path}')
print(f'📁 Tamaño: {pdf_path.stat().st_size / 1024:.1f} KB')
