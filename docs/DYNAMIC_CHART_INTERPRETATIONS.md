# Dynamic Chart Interpretation System

## Overview

This document describes the dynamic chart interpretation system for USD/CLP forex forecast reports. The system replaces static hardcoded text with **contextual, data-driven interpretations** that adapt to actual market conditions.

## Problem Statement

Previously, chart interpretations contained hardcoded values:

```python
# OLD - STATIC (❌ Bad)
explanation = (
    "IC 80% (banda naranja 932-943) para sizing de posiciones core..."
    "Amplitud actual de 11 pesos en IC 80% sugiere volatilidad moderada..."
)
```

**Issues:**
- Values (932-943, 11 pesos) are hardcoded and don't reflect actual data
- Interpretations don't change with market conditions
- Not professional - traders notice stale numbers immediately

## Solution: Dynamic Interpretation Functions

New system generates contextual text from real data:

```python
# NEW - DYNAMIC (✅ Good)
explanation = interpret_forecast_bands(forecast, bundle, "7d")
# Reads actual IC80 bounds: 937.2-948.5
# Calculates width: 11.3 pesos
# Generates: "IC 80% banda naranja (937.2-948.5) para sizing de posiciones core..."
```

## Implementation

### Module Structure

```
forex_core/reporting/
├── chart_interpretations.py  # NEW - Dynamic interpretation functions
├── builder.py                 # UPDATED - Calls dynamic functions
└── charting.py               # Unchanged - Generates charts
```

### Four Dynamic Interpretation Functions

#### 1. Chart 1A - Historical Overview

**File:** `/src/forex_core/reporting/chart_interpretations.py`

```python
def interpret_hist_overview(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str:
    """
    Generate interpretation for 30-day historical context + forecast.

    Dynamic Inputs:
    - Current price from bundle.usdclp_series[-1]
    - 30-day high/low from bundle.usdclp_series.tail(30)
    - Forecast endpoint from forecast.series[-1].mean
    - Price change % calculated dynamically

    Output Example:
    "Contexto 30d: USD/CLP en rango 935.2-940.8 tras rally alcista
    de +1.2% desde mínimo. Proyección 7d apunta a 937.9 (+0.11%),
    sesgo neutral. Mantener estrategia range-bound, vender volatilidad."
    """
```

**Professional Tone:**
- Market context: "rally alcista", "corrección bajista", "consolidación lateral"
- Trend analysis: "tercio superior del rango", "resistencia próxima"
- Actionable: "Cubrir exposiciones en retrocesos", "Oportunidad para exportadores"

#### 2. Chart 1B - Tactical Zoom

**File:** `/src/forex_core/reporting/chart_interpretations.py`

```python
def interpret_tactical_zoom(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str:
    """
    Generate interpretation for last 5 days + forecast WITH IC bands.

    Dynamic Inputs:
    - Last 5d range: bundle.usdclp_series.tail(5).min/max
    - IC80 bounds: forecast.series[-1].ci80_low/high
    - IC95 bounds: forecast.series[-1].ci95_low/high
    - Calculated: long/short entry levels, stops, targets
    - Calculated: Risk/Reward ratios

    Output Example:
    "Zona de trading últimos 5d: 937.2-938.5 (rango 1.3 pesos).
    IC 80% proyectado (937.0-938.3) define core range operativo;
    amplitud 1.3 pesos indica muy baja volatilidad.
    **Setup largo conservador:** Entry 937.0-937.2, stop 936.5,
    target 938.2 (R/R 2.4:1)."
    """
```

**Professional Tone:**
- Tactical levels: "Entry 937.0-937.2, stop 936.5, target 938.2"
- Position sizing: "Aumente tamaño posicional hasta 1.5x normal"
- Risk management: "stops ajustados 0.8-1%"
- R/R ratios: "R/R 2.4:1" calculated from actual levels

#### 3. Chart 2 - Forecast Bands

**File:** `/src/forex_core/reporting/chart_interpretations.py`

```python
def interpret_forecast_bands(
    forecast: ForecastResult,
    bundle: DataBundle,
    horizon: str = "7d",
) -> str:
    """
    Generate interpretation for forecast projection WITH confidence bands.

    Dynamic Inputs:
    - IC80 width: avg([p.ci80_high - p.ci80_low for p in forecast.series])
    - IC95 width: avg([p.ci95_high - p.ci95_low for p in forecast.series])
    - Volatility regime: derived from IC width
    - Forecast trajectory: calculated from price change %
    - Band dynamics: expanding/contracting/stable

    Output Example:
    "IC 80% banda naranja (932.1-943.2) define rango core para posiciones
    direccionales. Amplitud promedio IC 80% de 11.1 pesos indica volatilidad
    baja-moderada: Volatilidad normal, apropiado para estrategias direccionales
    estándar. **Position sizing:** Posiciones core 50-60%, stops 1-1.5%."
    """
```

**Professional Tone:**
- Volatility regimes: "muy baja", "baja-moderada", "moderada-alta", "alta"
- Position sizing: "Posiciones direccionales hasta 80% de capital"
- Strategy guidance: "favorece estrategias de opciones y hedging"
- Band dynamics: "bandas expandiéndose (incertidumbre creciente)"

#### 4. Chart 4 - Correlation Matrix

**File:** `/src/forex_core/reporting/chart_interpretations.py`

```python
def interpret_correlation_matrix(
    bundle: DataBundle,
    horizon: str = "7d",
) -> str:
    """
    Generate interpretation for correlation heatmap.

    Dynamic Inputs:
    - Correlation matrix computed from bundle series (USD/CLP, Copper, DXY, VIX, EEM)
    - Strongest correlation pair identified
    - Weakest correlation pair identified
    - Current copper price from bundle.indicators["copper"]

    Output Example:
    "**Leading indicator clave:** Cobre correlación inversa fuerte -0.68;
    precio actual 4.32 USD/lb, nivel crítico 4.10 (5% abajo) actuaría
    como trigger para depreciación CLP. **Hedge strategy:** Correlación
    DXY-CLP +0.76 permite hedge cruzado: Use futuros DXY con ratio 1:0.76.
    **Risk gauge:** VIX-EEM correlación -0.81 funciona como early warning
    de risk-off: Repuntes VIX >18 + caída EEM >-2% anticipan fortalecimiento
    USD/CLP en 48-72h."
    """
```

**Professional Tone:**
- Leading indicators: "Cobre con 24h de anticipación típica"
- Hedge strategies: "Use futuros DXY con ratio 1:0.76"
- Risk warnings: "Repuntes VIX >18 anticipan fortalecimiento USD/CLP"
- Decorrelation: "Útil para portfolio diversification"

### Integration with ReportBuilder

**File:** `/src/forex_core/reporting/builder.py`

```python
from .chart_interpretations import (
    interpret_hist_overview,
    interpret_tactical_zoom,
    interpret_forecast_bands,
    interpret_correlation_matrix,
)

def _build_chart_blocks(
    self,
    bundle: DataBundle,
    charts: Dict[str, Path],
    forecast: ForecastResult,  # NEW parameter
    horizon: str,              # NEW parameter
) -> List[Dict[str, str]]:
    """Build chart blocks with DYNAMIC explanations."""

    blocks = []

    # Chart 1A: Historical Overview (DYNAMIC)
    if "hist_overview" in charts:
        explanation = interpret_hist_overview(bundle, forecast, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["hist_overview"]),
            "title": "USD/CLP - Contexto Histórico + Proyección",
            "explanation": explanation,  # DYNAMIC TEXT
        })

    # Chart 1B: Tactical Zoom (DYNAMIC)
    if "tactical_zoom" in charts:
        explanation = interpret_tactical_zoom(bundle, forecast, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["tactical_zoom"]),
            "title": "USD/CLP - Zoom Táctico (Niveles de Trading)",
            "explanation": explanation,  # DYNAMIC TEXT
        })

    # Chart 2: Forecast Bands (DYNAMIC)
    if "forecast_bands" in charts:
        explanation = interpret_forecast_bands(forecast, bundle, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["forecast_bands"]),
            "title": "Bandas de Proyección (IC 80% / IC 95%)",
            "explanation": explanation,  # DYNAMIC TEXT
        })

    # Chart 4: Correlation Matrix (DYNAMIC)
    if "correlation" in charts:
        explanation = interpret_correlation_matrix(bundle, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["correlation"]),
            "title": "Matriz de Correlaciones",
            "explanation": explanation,  # DYNAMIC TEXT
        })

    return blocks
```

## Testing

### Unit Test Example

```python
from forex_core.reporting.chart_interpretations import interpret_tactical_zoom

def test_tactical_zoom_dynamic():
    """Test that interpretation adapts to data."""
    bundle = create_mock_bundle(current_price=940.0)
    forecast = create_mock_forecast(current_price=940.0)

    interp = interpret_tactical_zoom(bundle, forecast, "7d")

    # Verify interpretation contains actual data values
    assert "940" in interp  # Current price
    assert "IC 80%" in interp  # IC bands mentioned
    assert "Entry" in interp  # Entry levels provided
    assert "stop" in interp  # Stop levels provided
    assert "R/R" in interp  # Risk/reward ratio calculated
```

### Integration Test

Run demo script:

```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
python examples/test_dynamic_interpretations.py
```

**Expected Output:**
```
================================================================================
CHART 1A - HISTORICAL OVERVIEW (30d + forecast, no bands)
================================================================================
Contexto 30d: USD/CLP en rango 935.2-940.8 tras rally alcista de +1.2%
desde mínimo. Proyección 7d apunta a 937.9 (+0.11%), sesgo neutral.
Mantener estrategia range-bound, vender volatilidad. Precio actual 938.1
en tercio medio del rango 30d: zona neutral, aguarde breakout direccional.

================================================================================
CHART 1B - TACTICAL ZOOM (Last 5d + forecast WITH IC bands)
================================================================================
Zona de trading últimos 5d: 937.2-938.5 (rango 1.3 pesos). IC 80%
proyectado (937.0-938.3) define core range operativo; amplitud 1.3 pesos
indica muy baja volatilidad. IC 95% (935.5-940.8) marca límites extremos
para tail-risk hedge. **Setup largo conservador:** Entry 937.0-937.2,
stop 936.5, target 938.2 (R/R 2.4:1). **Setup corto:** Entry 938.1-938.3,
stop 941.3, target 937.8 (R/R 0.1:1). Aumente tamaño posicional hasta
1.5x normal, stops ajustados. Invalidación: quiebre sostenido fuera IC 95%.
```

## Benefits

### 1. Professional Credibility
- Interpretations always match chart data
- No stale/outdated numbers
- Traders trust dynamic content

### 2. Actionable Intelligence
- Specific entry/exit levels calculated
- Risk/reward ratios from actual IC bands
- Position sizing adapts to volatility

### 3. Maintainability
- No manual updates needed when data changes
- Single source of truth (data bundle)
- Consistent methodology across charts

### 4. Scalability
- Easy to add new interpretation logic
- Reusable across different forecast horizons (7d, 12m)
- Supports multiple currency pairs (future)

## File Locations

- **New Module:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/chart_interpretations.py`
- **Updated Builder:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/builder.py`
- **Test Script:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/examples/test_dynamic_interpretations.py`
- **This Doc:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/docs/DYNAMIC_CHART_INTERPRETATIONS.md`

## Next Steps

1. **Run Tests:**
   ```bash
   cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
   python examples/test_dynamic_interpretations.py
   ```

2. **Generate Full Report:**
   ```bash
   python -m services.forecaster_7d.cli --skip-email
   ```

3. **Review PDF Output:**
   - Check `/outputs/usdclp_report_7d_YYYYMMDD_HHMM.pdf`
   - Verify all interpretations have current values
   - Confirm professional trader-to-trader language

4. **Future Enhancements:**
   - Add interpretation for 12-month forecast horizon
   - Support multi-currency pairs (USD/EUR, USD/JPY)
   - Machine learning-enhanced interpretation templates
   - Backtesting interpretation accuracy vs actual moves

## Summary

This dynamic interpretation system transforms static chart captions into intelligent, contextual analysis that:

- Reads real data from DataBundle and ForecastResult
- Calculates trading levels (entry, stop, target) dynamically
- Provides risk/reward ratios from actual confidence intervals
- Adapts position sizing to volatility regime
- Generates correlation-based hedge strategies
- Uses professional trader-to-trader language
- Maintains credibility with always-current values

**Result:** Professional, actionable forex reports that traders can trust and act upon.
