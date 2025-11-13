# Chart Interpretations API Reference

Quick reference for dynamic chart interpretation functions.

## Module Import

```python
from forex_core.reporting.chart_interpretations import (
    interpret_hist_overview,
    interpret_tactical_zoom,
    interpret_forecast_bands,
    interpret_correlation_matrix,
    extract_correlation_metrics,
)
```

---

## Function 1: `interpret_hist_overview`

### Signature

```python
def interpret_hist_overview(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `bundle` | `DataBundle` | Data bundle with `usdclp_series` (30+ days) |
| `forecast` | `ForecastResult` | Forecast with `series` list of `ForecastPoint` |
| `horizon` | `str` | Forecast horizon label (e.g., "7d", "12m") |

### Dynamic Data Inputs Used

- `bundle.usdclp_series.tail(30)` - Last 30 days of historical prices
- `bundle.usdclp_series.iloc[-1]` - Current price
- `hist_30d.min()` / `hist_30d.max()` - 30-day range
- `forecast.series[-1].mean` - Forecast endpoint
- **Calculated:** 30-day price change %, forecast change %

### Sample Output

```text
Contexto 30d: USD/CLP en rango 935.2-940.8 tras rally alcista de +1.2% desde mínimo.
Proyección 7d apunta a 937.9 (+0.11%), sesgo neutral. Mantener estrategia range-bound,
vender volatilidad. Precio actual 938.1 en tercio medio del rango 30d: zona neutral,
aguarde breakout direccional.
```

### Professional Language Features

- Trend descriptions: "rally alcista", "corrección bajista", "consolidación lateral"
- Position in range: "tercio superior", "tercio medio", "tercio inferior"
- Actionable recommendations: "Cubrir exposiciones en retrocesos"
- Market context: "resistencia próxima 940.8, cautela en longas"

---

## Function 2: `interpret_tactical_zoom`

### Signature

```python
def interpret_tactical_zoom(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `bundle` | `DataBundle` | Data bundle with `usdclp_series` (5+ days) |
| `forecast` | `ForecastResult` | Forecast with IC bands at endpoint |
| `horizon` | `str` | Forecast horizon label |

### Dynamic Data Inputs Used

- `bundle.usdclp_series.tail(5)` - Last 5 days
- `hist_5d.min()` / `hist_5d.max()` - 5-day trading range
- `forecast.series[-1].ci80_low/high` - IC 80% bounds
- `forecast.series[-1].ci95_low/high` - IC 95% bounds
- **Calculated:** Entry levels, stop levels, target levels, R/R ratios

### Sample Output

```text
Zona de trading últimos 5d: 937.2-938.5 (rango 1.3 pesos). IC 80% proyectado
(937.0-938.3) define core range operativo; amplitud 1.3 pesos indica muy baja
volatilidad. IC 95% (935.5-940.8) marca límites extremos para tail-risk hedge.
**Setup largo conservador:** Entry 937.0-937.2, stop 936.5, target 938.2 (R/R 2.4:1).
**Setup corto:** Entry 938.1-938.3, stop 941.3, target 937.8 (R/R 0.1:1).
Aumente tamaño posicional hasta 1.5x normal, stops ajustados.
Invalidación: quiebre sostenido fuera IC 95%.
```

### Professional Language Features

- Tactical levels: "Entry 937.0-937.2, stop 936.5, target 938.2"
- Risk metrics: "R/R 2.4:1" (calculated dynamically)
- Position sizing: "Aumente tamaño posicional hasta 1.5x normal"
- Volatility regime: "muy baja", "baja-moderada", "moderada-alta", "alta"
- Invalidation rules: "quiebre sostenido fuera IC 95%"

---

## Function 3: `interpret_forecast_bands`

### Signature

```python
def interpret_forecast_bands(
    forecast: ForecastResult,
    bundle: DataBundle,
    horizon: str = "7d",
) -> str
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `forecast` | `ForecastResult` | Forecast with confidence intervals |
| `bundle` | `DataBundle` | Data bundle for current price context |
| `horizon` | `str` | Forecast horizon label |

### Dynamic Data Inputs Used

- `bundle.usdclp_series.iloc[-1]` - Current price
- `forecast.series[-1].mean` - Forecast endpoint mean
- `forecast.series[-1].ci80_low/high` - IC 80% at endpoint
- `forecast.series[-1].ci95_low/high` - IC 95% at endpoint
- **Calculated:** Average IC widths, volatility regime, band dynamics

### Sample Output

```text
IC 80% banda naranja (932.1-943.2) define rango core para posiciones direccionales
y stops técnicos. IC 95% banda violeta (925.5-950.8) marca niveles extremos para
oportunidades contrarian o tail-risk hedging. Amplitud promedio IC 80% de 11.1 pesos
indica volatilidad baja-moderada: Volatilidad normal, apropiado para estrategias
direccionales estándar. Proyección central 937.5 CLP muestra trayectoria neutral;
Sin sesgo direccional claro; considere estrategias neutral-delta (iron condors,
butterfly spreads). Dinámica temporal: bandas estables; Mantenga sizing consistente
durante el horizonte. **Position sizing:** Posiciones core 50-60%, stops 1-1.5%.
**Triggers gestión:** Si IC 80% expande >14.4 pesos, corte posiciones a 50%;
si contrae <7.8 pesos, suba exposición hasta 120% normal.
```

### Professional Language Features

- Volatility regimes: "muy baja", "baja-moderada", "moderada-alta", "alta"
- Position sizing advice: "Posiciones core 50-60%, stops 1-1.5%"
- Strategy recommendations: "favorece estrategias de opciones y hedging"
- Band dynamics: "bandas expandiéndose", "bandas contrayéndose", "bandas estables"
- Trigger levels: "Si IC 80% expande >14.4 pesos, corte posiciones a 50%"

---

## Function 4: `interpret_correlation_matrix`

### Signature

```python
def interpret_correlation_matrix(
    bundle: DataBundle,
    horizon: str = "7d",
) -> str
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `bundle` | `DataBundle` | Data bundle with multiple series (USD/CLP, Copper, DXY, VIX, EEM) |
| `horizon` | `str` | Forecast horizon label |

### Dynamic Data Inputs Used

- `bundle.usdclp_series` - USD/CLP prices
- `bundle.copper_series` - Copper prices
- `bundle.dxy_series` (optional) - DXY index
- `bundle.vix_series` (optional) - VIX volatility index
- `bundle.eem_series` (optional) - EEM emerging markets ETF
- `bundle.indicators["copper"].value` - Current copper price
- **Calculated:** Correlation matrix, strongest/weakest pairs

### Sample Output

```text
**Leading indicator clave:** Cobre correlación inversa fuerte -0.68; precio actual
4.32 USD/lb, nivel crítico 4.10 (5% abajo) actuaría como trigger para depreciación CLP.
Leading indicator con ~24h de anticipación típica. **Hedge strategy:** Correlación
DXY-CLP +0.76 permite hedge cruzado: Use futuros DXY (más líquidos) para cubrir
exposición CLP con ratio 1:0.76. Quiebre DXY sobre 105 pts señaliza presión USD/CLP
alcista. **Risk gauge:** VIX-EEM correlación -0.81 funciona como early warning de
risk-off: Repuntes VIX >18 + caída EEM >-2% anticipan fortalecimiento USD/CLP en
48-72h. VIX-CLP correlación +0.32, EEM-CLP correlación -0.45. **Decorrelación:**
Decorrelación táctica con []: Útil para portfolio diversification y reducción de
riesgo concentrado. Correlación más fuerte: DXY (+0.76), más débil: VIX (+0.32).
Use correlaciones >0.7 para hedging, <0.3 para diversificación.
```

### Professional Language Features

- Leading indicators: "Cobre con ~24h de anticipación típica"
- Hedge strategies: "Use futuros DXY con ratio 1:0.76"
- Critical levels: "nivel crítico 4.10 (5% abajo)"
- Risk warnings: "Repuntes VIX >18 anticipan fortalecimiento USD/CLP en 48-72h"
- Correlation thresholds: "Use correlaciones >0.7 para hedging, <0.3 para diversificación"

---

## Utility Function: `extract_correlation_metrics`

### Signature

```python
def extract_correlation_metrics(
    bundle: DataBundle
) -> Dict[str, float]
```

### Returns

Dictionary mapping correlation pair names to coefficients:

```python
{
    "USD/CLP_Cobre": -0.68,
    "USD/CLP_DXY": 0.76,
    "USD/CLP_VIX": 0.32,
    "USD/CLP_EEM": -0.45,
    "VIX_EEM": -0.81,
}
```

### Usage Example

```python
corr_metrics = extract_correlation_metrics(bundle)
copper_corr = corr_metrics["USD/CLP_Cobre"]
print(f"Copper correlation: {copper_corr:.2f}")
# Output: Copper correlation: -0.68
```

---

## Integration Example

### In ReportBuilder

```python
from forex_core.reporting.chart_interpretations import (
    interpret_hist_overview,
    interpret_tactical_zoom,
    interpret_forecast_bands,
    interpret_correlation_matrix,
)

def _build_chart_blocks(self, bundle, charts, forecast, horizon):
    blocks = []

    # Chart 1A - DYNAMIC
    if "hist_overview" in charts:
        explanation = interpret_hist_overview(bundle, forecast, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["hist_overview"]),
            "title": "USD/CLP - Contexto Histórico + Proyección",
            "explanation": explanation,
        })

    # Chart 1B - DYNAMIC
    if "tactical_zoom" in charts:
        explanation = interpret_tactical_zoom(bundle, forecast, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["tactical_zoom"]),
            "title": "USD/CLP - Zoom Táctico (Niveles de Trading)",
            "explanation": explanation,
        })

    # Chart 2 - DYNAMIC
    if "forecast_bands" in charts:
        explanation = interpret_forecast_bands(forecast, bundle, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["forecast_bands"]),
            "title": "Bandas de Proyección (IC 80% / IC 95%)",
            "explanation": explanation,
        })

    # Chart 4 - DYNAMIC
    if "correlation" in charts:
        explanation = interpret_correlation_matrix(bundle, horizon)
        blocks.append({
            "image": ChartGenerator.image_to_base64(charts["correlation"]),
            "title": "Matriz de Correlaciones",
            "explanation": explanation,
        })

    return blocks
```

---

## Error Handling

All functions include fallback logic when data is incomplete:

```python
# Example: Correlation matrix with missing data
if not correlations:
    return (
        "Matriz de correlaciones no disponible con datos actuales. "
        "Requiere series temporales de Cobre, DXY, VIX y EEM para análisis completo."
    )
```

---

## Testing

### Unit Test Template

```python
import pytest
from forex_core.reporting.chart_interpretations import interpret_tactical_zoom

def test_tactical_zoom_dynamic():
    """Test that tactical zoom interpretation uses real data."""
    bundle = create_mock_bundle(current_price=940.0)
    forecast = create_mock_forecast(current_price=940.0, ic80_width=10.0)

    interp = interpret_tactical_zoom(bundle, forecast, "7d")

    # Verify dynamic values appear in text
    assert "940" in interp  # Current price
    assert "Entry" in interp  # Entry levels
    assert "stop" in interp  # Stop levels
    assert "R/R" in interp  # Risk/reward ratio

    # Verify structure
    assert "IC 80%" in interp
    assert "IC 95%" in interp
    assert "Setup largo" in interp or "Setup corto" in interp
```

### Integration Test

```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
python examples/test_dynamic_interpretations.py
```

---

## Summary

| Chart | Function | Key Outputs |
|-------|----------|-------------|
| **1A - Historical Overview** | `interpret_hist_overview` | 30d context, trend, forecast bias |
| **1B - Tactical Zoom** | `interpret_tactical_zoom` | Entry/stop/target levels, R/R ratios |
| **2 - Forecast Bands** | `interpret_forecast_bands` | Position sizing, volatility regime |
| **4 - Correlation Matrix** | `interpret_correlation_matrix` | Hedge strategies, leading indicators |

**All functions:**
- Read real data (no hardcoded values)
- Generate professional trader-to-trader language
- Provide actionable recommendations with specific levels
- Adapt to market conditions dynamically
