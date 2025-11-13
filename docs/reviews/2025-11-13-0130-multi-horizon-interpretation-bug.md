# Code Review: Multi-Horizon Forecast Interpretation System

**Fecha:** 2025-11-13 01:30
**Revisor:** Code Reviewer Agent
**Archivos revisados:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/chart_interpretations.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/builder.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/config/constants.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/config.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_15d/config.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_30d/config.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_90d/config.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_15d/pipeline.py`

**Complejidad del cambio:** Moderado

---

## ⚡ TL;DR (Resumen Ejecutivo)

**Veredicto General:** 🔴 Requiere cambios críticos

**Impacto del cambio:** Alto - Afecta la calidad de todos los reportes multi-horizonte

**Principales hallazgos:**
- 🔴 **CRITICAL BUG**: `service_config.horizon` siempre retorna `"daily"` en vez de `"7d"`, `"15d"`, `"30d"`, `"90d"`
- 🔴 Las funciones de interpretación reciben `horizon="daily"` pero esperan `"7d"`, `"15d"`, etc.
- 🔴 Hardcoded references: "últimos 5d", "30d", "5-day scenarios" no se ajustan por horizonte
- 🟡 Falta lógica horizon-aware para escalar escenarios (2 semanas vs 3 meses vs trimestre)
- 🟡 Interpretaciones técnicas y macro no consideran diferencia entre horizontes tácticos vs estratégicos

**Acción recomendada:** Requiere refactor - Implementar horizon mapping y scenario scaling

---

## 📊 Métricas del Código

| Métrica | Valor | Status |
|---------|-------|--------|
| Archivos modificados | 8 | ℹ️ |
| Líneas de código revisadas | ~1,200 | ℹ️ |
| Issues críticos identificados | 3 | 🔴 |
| Funciones afectadas | 4 | 🔴 |
| Complejidad ciclomática (max) | 8 | 🟢 |
| Funciones >30 líneas | 4 | 🟡 |
| Código duplicado | Bajo | 🟢 |

---

## 🔍 Análisis Detallado

### 1. Arquitectura y Diseño [🔴 CRITICAL]

#### 🔴 Issues Críticos:

**Issue #1: Horizon Mismatch - Config vs Interpretation Layer**
- **Archivos:**
  - `src/services/forecaster_15d/config.py:48`
  - `src/forex_core/reporting/chart_interpretations.py:25,96,189`
  - `src/services/forecaster_15d/pipeline.py:179`
- **Problema:** Los service configs definen `horizon: Literal["daily"] = "daily"` para TODOS los horizontes (7d, 15d, 30d, 90d), pero las funciones de interpretación esperan horizon codes específicos como `"7d"`, `"15d"`, etc.

- **Código problemático:**
  ```python
  # En forecaster_15d/config.py (línea 48)
  @dataclass(frozen=True)
  class Forecaster15DConfig:
      horizon: Literal["daily"] = "daily"  # ❌ WRONG - Should be "15d"
      projection_days: int = PROJECTION_DAYS_15D  # 15 days
  ```

  ```python
  # Pipeline pasa service_config.horizon (línea 179)
  return builder.build(
      bundle=bundle,
      forecast=forecast,
      artifacts=artifacts_dict,
      charts=chart_paths,
      horizon=service_config.horizon,  # ❌ This is "daily", not "15d"!
  )
  ```

  ```python
  # Interpretación recibe "daily" pero la usa en string templates (línea 84)
  interpretation = (
      f"Contexto 30d: USD/CLP en rango {low_30d:.1f}-{high_30d:.1f} tras {trend_verb} {trend_30d} "
      f"de {abs(price_change_30d):+.1f}% desde mínimo. Proyección {horizon} apunta a..."
      # ❌ Esto imprime "Proyección daily apunta a..." en vez de "Proyección 15d apunta a..."
  )
  ```

- **Impacto:**
  - Los reportes 15d/30d/90d tienen interpretaciones genéricas con "daily" en vez del horizonte específico
  - No hay diferenciación entre horizonte táctico (7d), corto plazo (15d), medio plazo (30d) y trimestral (90d)
  - Los usuarios reciben el mismo análisis para 7 días que para 90 días

- **Solución sugerida:**
  ```python
  # OPCIÓN A: Cambiar service configs para usar horizon codes
  # En forecaster_15d/config.py
  @dataclass(frozen=True)
  class Forecaster15DConfig:
      horizon: Literal["15d"] = "15d"  # ✅ Specific horizon code
      projection_days: int = PROJECTION_DAYS_15D

      @property
      def horizon_type(self) -> Literal["daily", "monthly"]:
          """Frequency type for forecasting engine."""
          return "daily"
  ```

  ```python
  # OPCIÓN B: Agregar método en config para obtener horizon code
  @dataclass(frozen=True)
  class Forecaster15DConfig:
      horizon: Literal["daily"] = "daily"  # For ForecastEngine
      projection_days: int = PROJECTION_DAYS_15D

      @property
      def horizon_code(self) -> str:
          """Horizon code for reporting/interpretation."""
          return "15d"
  ```

  ```python
  # Actualizar pipeline para pasar horizon_code en vez de horizon
  # En pipeline.py:179
  return builder.build(
      bundle=bundle,
      forecast=forecast,
      artifacts=artifacts_dict,
      charts=chart_paths,
      horizon=service_config.horizon_code,  # ✅ Now passes "15d"
  )
  ```

- **Razón:** Separar concerns - `horizon="daily"` es para el ForecastEngine (frecuencia), mientras que `horizon_code="15d"` es para reportes (contexto de negocio)

---

**Issue #2: Hardcoded Timeframes en Chart Interpretations**
- **Archivo:** `src/forex_core/reporting/chart_interpretations.py`
- **Problema:** Las funciones de interpretación tienen hardcoded references a "30d", "5d", etc., que no escalan según el horizonte del forecast.

- **Ejemplos específicos:**

  ```python
  # Línea 47-48: Hardcoded 30d lookback
  def interpret_hist_overview(...):
      hist_30d = bundle.usdclp_series.tail(30)  # ❌ HARDCODED
      current_price = hist_30d.iloc[-1]

      # Línea 83: Output también hardcoded
      interpretation = (
          f"Contexto 30d: USD/CLP en rango..."  # ❌ HARDCODED
      )
  ```

  ```python
  # Línea 117-122: Hardcoded 5d zoom
  def interpret_tactical_zoom(...):
      hist_5d = bundle.usdclp_series.tail(5)  # ❌ HARDCODED
      current_price = hist_5d.iloc[-1]
      high_5d = hist_5d.max()
      low_5d = hist_5d.min()
      range_5d = high_5d - low_5d

      interpretation = (
          f"Zona de trading últimos 5d: {low_5d:.1f}-{high_5d:.1f}..."  # ❌ HARDCODED
      )
  ```

- **Impacto:**
  - Reporte de 90 días muestra "Contexto 30d" (inadecuado - debería ser "Contexto 180d")
  - Reporte de 90 días muestra "Zoom últimos 5d" (demasiado táctico - debería ser "últimos 30d")
  - Usuarios de 30d/90d reciben análisis de contexto demasiado corto

- **Solución sugerida:**
  ```python
  # Implementar horizon-aware lookback scaling
  def interpret_hist_overview(
      bundle: DataBundle,
      forecast: ForecastResult,
      horizon: str = "7d",
  ) -> str:
      """
      Generate professional interpretation for Chart 1A - Historical Overview.

      Dynamically adjusts lookback period based on forecast horizon:
      - 7d forecast: 30d context
      - 15d forecast: 60d context
      - 30d forecast: 90d context
      - 90d forecast: 180d context
      """
      # ✅ DYNAMIC LOOKBACK
      lookback_map = {
          "7d": 30,
          "15d": 60,
          "30d": 90,
          "90d": 180,
          "12m": 365,
      }
      lookback_days = lookback_map.get(horizon, 30)

      hist_context = bundle.usdclp_series.tail(lookback_days)
      current_price = hist_context.iloc[-1]
      high = hist_context.max()
      low = hist_context.min()

      # Calculate trend over lookback period
      price_change = ((current_price / hist_context.iloc[0]) - 1) * 100

      # ✅ DYNAMIC OUTPUT TEXT
      interpretation = (
          f"Contexto {lookback_days}d: USD/CLP en rango {low:.1f}-{high:.1f} tras..."
      )

      return interpretation
  ```

  ```python
  # Tactical zoom también debe escalar
  def interpret_tactical_zoom(
      bundle: DataBundle,
      forecast: ForecastResult,
      horizon: str = "7d",
  ) -> str:
      """
      Generate professional interpretation for Chart 1B - Tactical Zoom.

      Dynamically adjusts tactical window based on forecast horizon:
      - 7d forecast: 5d zoom (daily trading)
      - 15d forecast: 10d zoom (weekly trading)
      - 30d forecast: 15d zoom (bi-weekly trading)
      - 90d forecast: 30d zoom (monthly trading)
      """
      # ✅ DYNAMIC ZOOM WINDOW
      zoom_map = {
          "7d": 5,
          "15d": 10,
          "30d": 15,
          "90d": 30,
          "12m": 60,
      }
      zoom_days = zoom_map.get(horizon, 5)

      hist_zoom = bundle.usdclp_series.tail(zoom_days)
      current_price = hist_zoom.iloc[-1]
      high_zoom = hist_zoom.max()
      low_zoom = hist_zoom.min()
      range_zoom = high_zoom - low_zoom

      # ✅ DYNAMIC OUTPUT
      interpretation = (
          f"Zona de trading últimos {zoom_days}d: {low_zoom:.1f}-{high_zoom:.1f} "
          f"(rango {range_zoom:.1f} pesos). ..."
      )

      return interpretation
  ```

- **Razón:** Los usuarios de diferentes horizontes tienen diferentes necesidades de contexto temporal. Un trader buscando forecast de 90 días necesita ver contexto de 6 meses, no 30 días.

---

**Issue #3: Falta Horizon-Specific Scenario Framing**
- **Archivo:** `src/forex_core/reporting/chart_interpretations.py` - Todas las funciones
- **Problema:** Las interpretaciones no ajustan el framing de escenarios según horizonte. Usan mismo lenguaje táctico para 7d y 90d.

- **Ejemplos:**

  ```python
  # Línea 73-79: Mismo framing para todos los horizontes
  if forecast_change > 0.3:
      forecast_bias = "sesgo alcista confirmado"
      action = "Cubrir exposiciones importadoras en retrocesos"  # ❌ Muy táctico para 90d
  elif forecast_change < -0.3:
      forecast_bias = "sesgo bajista emergente"
      action = "Oportunidad para exportadores asegurar niveles elevados"  # ❌ Muy táctico
  else:
      forecast_bias = "sesgo neutral"
      action = "Mantener estrategia range-bound, vender volatilidad"  # ❌ Opciones talk para 90d
  ```

  ```python
  # Línea 138-146: Volatility sizing advice igual para todos
  if ic80_width < 8:
      vol_regime = "baja volatilidad"
      sizing_advice = "Aumente tamaño posicional hasta 1.5x normal, stops ajustados"
      # ❌ Esto es day-trading advice, NO apropiado para 90d forecast
  ```

- **Impacto:**
  - Usuarios de 90d forecast reciben consejos de "stops ajustados" y "tamaño posicional 1.5x" (day-trading advice)
  - No hay diferenciación entre:
    - **7d (Tactical)**: Niveles específicos, stops tight, opciones semanales
    - **15d (Short-term)**: Zonas de entrada, hedge escalonado, opciones 2-semana
    - **30d (Medium-term)**: Tendencias mensuales, forwards 1M, estrategia trimestral
    - **90d (Strategic)**: Ciclos macroeconómicos, forwards 3M, planificación semestral

- **Solución sugerida:**
  ```python
  # Agregar horizon-specific scenario framing
  def _get_horizon_framing(horizon: str) -> dict:
      """
      Get horizon-specific framing parameters for interpretations.

      Returns dict with:
      - timeframe_label: "próximos X días/semanas/meses"
      - trading_style: "intradía", "semanal", "mensual", "trimestral"
      - instruments: "opciones diarias", "forwards 1M", etc.
      - volatility_context: "intraday vol", "30d realized vol", etc.
      """
      framings = {
          "7d": {
              "timeframe_label": "próxima semana",
              "trading_style": "táctico (1-5 días)",
              "instruments": ["opciones semanales", "spot", "forwards overnight"],
              "volatility_context": "volatilidad intraday y semanal",
              "decision_urgency": "alta - decisiones diarias",
              "scenario_focus": "niveles técnicos específicos y triggers corto plazo",
          },
          "15d": {
              "timeframe_label": "próximas 2 semanas",
              "trading_style": "corto plazo (1-2 semanas)",
              "instruments": ["forwards 15d", "opciones quincenales", "swaps cortos"],
              "volatility_context": "volatilidad bi-semanal",
              "decision_urgency": "media - decisiones semanales",
              "scenario_focus": "tendencias de 2 semanas, eventos macroeconómicos próximos",
          },
          "30d": {
              "timeframe_label": "próximo mes",
              "trading_style": "medio plazo (mensual)",
              "instruments": ["forwards 1M-2M", "opciones mensuales", "collars"],
              "volatility_context": "volatilidad mensual realizada",
              "decision_urgency": "baja - decisiones bi-semanales",
              "scenario_focus": "ciclos mensuales, publicaciones macro clave, tendencias trimestrales",
          },
          "90d": {
              "timeframe_label": "próximo trimestre",
              "trading_style": "estratégico (trimestral)",
              "instruments": ["forwards 3M-6M", "opciones trimestrales", "structured products"],
              "volatility_context": "volatilidad trimestral y ciclos estacionales",
              "decision_urgency": "muy baja - decisiones mensuales",
              "scenario_focus": "ciclos macroeconómicos, tendencias fundamentales, shocks estructurales",
          },
      }
      return framings.get(horizon, framings["7d"])
  ```

  ```python
  # Usar framing en interpretaciones
  def interpret_hist_overview(
      bundle: DataBundle,
      forecast: ForecastResult,
      horizon: str = "7d",
  ) -> str:
      # ... existing code ...

      framing = _get_horizon_framing(horizon)

      # Forecast bias con horizon-appropriate actions
      if forecast_change > 0.3:
          forecast_bias = "sesgo alcista confirmado"
          # ✅ HORIZON-SPECIFIC ACTIONS
          if horizon == "7d":
              action = "Cubrir exposiciones importadoras en retrocesos intraday"
          elif horizon == "15d":
              action = "Estrategia de cobertura escalonada en próximas 2 semanas"
          elif horizon == "30d":
              action = "Considerar forwards 1M-2M para asegurar márgenes trimestrales"
          elif horizon == "90d":
              action = "Planificar estrategia de cobertura trimestral con forwards 3M-6M y opciones estructuradas"
      # ... similar for other scenarios

      interpretation = (
          f"Contexto {lookback_days}d: USD/CLP en rango {low:.1f}-{high:.1f}. "
          f"Proyección {framing['timeframe_label']} apunta a {forecast_end.mean:.1f} "
          f"({forecast_change:+.2f}%), {forecast_bias}. "
          f"{action}. "
          f"<strong>Enfoque {framing['trading_style']}:</strong> {framing['scenario_focus']}."
      )

      return interpretation
  ```

- **Razón:** Diferentes horizontes de forecast requieren diferentes estrategias de trading/hedging. Un forecast de 90 días NO debe dar consejos de "stops ajustados" o "sizing 1.5x" - eso es para day traders, no para CFOs planificando coberturas trimestrales.

---

### 2. Legibilidad y Mantenibilidad [🟡 Needs Improvement]

#### ✅ Aspectos Positivos:
- Nombres de funciones claros y descriptivos (`interpret_hist_overview`, `interpret_tactical_zoom`)
- Buena separación de concerns (cada función interpreta un chart específico)
- Docstrings completas con ejemplos
- Código bien estructurado con secciones lógicas (Extract data → Calculate metrics → Build interpretation)

#### 🟡 Sugerencias de Mejora:

**Sugerencia #1: Extract Magic Numbers to Horizon-Aware Constants**
- **Archivo:** `chart_interpretations.py:47,117,138,232`
- **Actual:**
  ```python
  hist_30d = bundle.usdclp_series.tail(30)  # Magic number
  hist_5d = bundle.usdclp_series.tail(5)    # Magic number
  if ic80_width < 8:  # Magic threshold
  elif avg_ic80_width < 12:  # Magic threshold
  ```
- **Sugerido:**
  ```python
  # At module level or in constants.py
  HORIZON_PARAMS = {
      "7d": {
          "hist_context_days": 30,
          "tactical_zoom_days": 5,
          "ic80_low_threshold": 8,
          "ic80_moderate_threshold": 12,
          "ic80_high_threshold": 18,
      },
      "15d": {
          "hist_context_days": 60,
          "tactical_zoom_days": 10,
          "ic80_low_threshold": 12,
          "ic80_moderate_threshold": 18,
          "ic80_high_threshold": 25,
      },
      # ... etc
  }

  # In function
  params = HORIZON_PARAMS.get(horizon, HORIZON_PARAMS["7d"])
  hist_context = bundle.usdclp_series.tail(params["hist_context_days"])
  ```
- **Beneficio:** Facilita ajustes de thresholds por horizonte, más mantenible, autoconfigurable

**Sugerencia #2: Consolidar Lógica de Trend/Bias Determination**
- **Archivo:** `chart_interpretations.py:60-79, 251-260, 527-535`
- **Problema:** Lógica duplicada para determinar trend/bias aparece en 3 funciones diferentes
- **Sugerido:**
  ```python
  def _determine_trend_bias(
      price_change_pct: float,
      horizon: str = "7d"
  ) -> Tuple[str, str, str]:
      """
      Determine trend direction, bias, and action based on price change.

      Returns: (trend_label, bias_description, action_recommendation)
      """
      # Adjust thresholds by horizon
      threshold_map = {
          "7d": 0.5,   # 0.5% for 7d
          "15d": 1.0,  # 1.0% for 15d
          "30d": 2.0,  # 2.0% for 30d
          "90d": 5.0,  # 5.0% for 90d
      }
      threshold = threshold_map.get(horizon, 0.5)

      if price_change_pct > threshold:
          return ("alcista", "depreciación del peso", _get_bullish_action(horizon))
      elif price_change_pct < -threshold:
          return ("bajista", "apreciación del peso", _get_bearish_action(horizon))
      else:
          return ("lateral", "estabilidad", _get_neutral_action(horizon))
  ```
- **Beneficio:** DRY principle, consistencia across interpretations, fácil ajustar thresholds

---

### 3. Performance y Eficiencia [🟢 Good]

**No issues críticos de performance identificados.**

✅ Aspectos positivos:
- Uso eficiente de pandas (`.tail()`, `.iloc[-1]`)
- No hay loops innecesarios
- Cálculos vectorizados donde apropiado (`pct_change()`, `.corr()`)
- Lazy evaluation (solo calcula métricas cuando se necesitan)

⚠️ Minor optimization opportunity:
- Línea 355-356: `corr_returns = corr_data.pct_change(fill_method=None).dropna()` podría cachear returns si se llama múltiples veces
- Considerar agregar `@lru_cache` para `_get_horizon_framing()` si se implementa

---

### 4. Error Handling y Robustez [🟢 Good]

✅ Aspectos positivos:
- Buen manejo de series opcionales (DXY, VIX, EEM) con checks de `hasattr()` y `len() > 0`
- Fallbacks apropiados cuando datos no están disponibles (líneas 359-365, 386-390)
- Explicit NaN handling en correlaciones (líneas 373-379)
- Try-except en métodos de builder para datos insuficientes

⚠️ Minor improvements:
- Agregar validación de `horizon` parameter en funciones de interpretación:
  ```python
  def interpret_hist_overview(
      bundle: DataBundle,
      forecast: ForecastResult,
      horizon: str = "7d",
  ) -> str:
      # ✅ ADD VALIDATION
      valid_horizons = ["7d", "15d", "30d", "90d", "12m"]
      if horizon not in valid_horizons:
          logger.warning(f"Invalid horizon '{horizon}', defaulting to '7d'")
          horizon = "7d"

      # ... rest of function
  ```

---

### 5. Testing y Testabilidad [🟡 Needs Tests]

**Tests existentes:** No encontrados para `chart_interpretations.py`

**Cobertura estimada:** 0% (no hay tests unitarios visibles)

#### 🔴 Critical: Falta Tests Para Lógica Horizon-Aware

**Tests requeridos:**

```python
# tests/unit/reporting/test_chart_interpretations.py

import pytest
from forex_core.reporting.chart_interpretations import (
    interpret_hist_overview,
    interpret_tactical_zoom,
    interpret_forecast_bands,
    _get_horizon_framing,  # If implemented
)


class TestHorizonAwareInterpretations:
    """Test that interpretations adjust correctly by horizon."""

    def test_hist_overview_adjusts_lookback_by_horizon(self, mock_bundle, mock_forecast):
        """7d should look back 30d, 90d should look back 180d."""
        interp_7d = interpret_hist_overview(mock_bundle, mock_forecast, "7d")
        interp_90d = interpret_hist_overview(mock_bundle, mock_forecast, "90d")

        assert "Contexto 30d" in interp_7d
        assert "Contexto 180d" in interp_90d
        assert interp_7d != interp_90d  # Must be different!

    def test_tactical_zoom_adjusts_window_by_horizon(self, mock_bundle, mock_forecast):
        """7d should zoom 5d, 90d should zoom 30d."""
        interp_7d = interpret_tactical_zoom(mock_bundle, mock_forecast, "7d")
        interp_90d = interpret_tactical_zoom(mock_bundle, mock_forecast, "90d")

        assert "últimos 5d" in interp_7d
        assert "últimos 30d" in interp_90d

    def test_forecast_bands_adjusts_sizing_advice_by_horizon(self, mock_bundle, mock_forecast):
        """7d should give day-trading advice, 90d should give strategic advice."""
        interp_7d = interpret_forecast_bands(mock_forecast, mock_bundle, "7d")
        interp_90d = interpret_forecast_bands(mock_forecast, mock_bundle, "90d")

        # 7d should mention tight stops
        assert "stops ajustados" in interp_7d or "0.8-1%" in interp_7d

        # 90d should NOT mention day-trading tactics
        assert "forwards 3M" in interp_90d or "trimestral" in interp_90d
        assert "stops ajustados" not in interp_90d  # No day-trading for 90d!

    def test_invalid_horizon_defaults_to_7d(self, mock_bundle, mock_forecast):
        """Invalid horizon should default gracefully."""
        interp = interpret_hist_overview(mock_bundle, mock_forecast, "invalid")
        assert interp is not None  # Should not crash
        # Should use 7d defaults
        assert "Contexto 30d" in interp


class TestCorrelationMatrixInterpretation:
    """Test correlation matrix interpretation logic."""

    def test_handles_missing_optional_series(self, bundle_without_vix):
        """Should gracefully handle missing VIX/EEM data."""
        interp = interpret_correlation_matrix(bundle_without_vix, "7d")
        assert "Indicadores de riesgo global" in interp or "Cobre" in interp

    def test_copper_correlation_interpretation(self, bundle_with_strong_copper_corr):
        """Should identify strong copper correlation and provide actionable advice."""
        interp = interpret_correlation_matrix(bundle_with_strong_copper_corr, "7d")
        assert "Cobre" in interp
        assert "correlación" in interp.lower()
```

**Prioridad:** Alta - Sin tests, los cambios propuestos podrían romper reportes existentes

---

### 6. Seguridad [🟢 Good]

No hay issues de seguridad críticos identificados.

✅ El módulo no maneja:
- User input directo
- Secrets o credenciales
- Operaciones de filesystem sin validación
- SQL queries
- Ejecución de código dinámico

---

## 🎯 Action Items

### 🔴 Crítico (Must Fix antes de merge):

- [ ] **[CRIT-1]** Fix horizon mismatch en service configs
  - **Archivo:** `src/services/forecaster_{15d,30d,90d}/config.py`
  - **Cambio:** Agregar `@property def horizon_code(self) -> str` que retorne "15d", "30d", "90d"
  - **O alternativamente:** Cambiar `horizon: Literal["daily"]` a `horizon: Literal["15d"]`, etc., y agregar `horizon_type` property
  - **Archivo:** `src/services/forecaster_{15d,30d,90d}/pipeline.py:179`
  - **Cambio:** Pasar `service_config.horizon_code` en vez de `service_config.horizon`

- [ ] **[CRIT-2]** Implementar horizon-aware lookback en `interpret_hist_overview()`
  - **Archivo:** `src/forex_core/reporting/chart_interpretations.py:47-90`
  - **Cambio:** Reemplazar `hist_30d = bundle.usdclp_series.tail(30)` con lookback map dinámico
  - **Lookback map:** `{"7d": 30, "15d": 60, "30d": 90, "90d": 180, "12m": 365}`

- [ ] **[CRIT-3]** Implementar horizon-aware zoom en `interpret_tactical_zoom()`
  - **Archivo:** `src/forex_core/reporting/chart_interpretations.py:117-183`
  - **Cambio:** Reemplazar `hist_5d = bundle.usdclp_series.tail(5)` con zoom map dinámico
  - **Zoom map:** `{"7d": 5, "15d": 10, "30d": 15, "90d": 30, "12m": 60}`

### 🟡 Importante (Should Fix):

- [ ] **[IMP-1]** Implementar `_get_horizon_framing()` utility function
  - **Archivo:** Agregar a `chart_interpretations.py` (nuevo helper)
  - **Retorna:** Dict con timeframe_label, trading_style, instruments, scenario_focus
  - **Usar en:** Todas las funciones `interpret_*()` para generar recomendaciones horizon-appropriate

- [ ] **[IMP-2]** Ajustar volatility sizing advice por horizonte en `interpret_forecast_bands()`
  - **Archivo:** `chart_interpretations.py:232-247`
  - **Cambio:** 7d da consejos de day-trading, 90d da consejos de strategic hedging
  - **Ejemplo 7d:** "Posiciones direccionales 80%, stops ajustados 0.8-1%"
  - **Ejemplo 90d:** "Forwards 3M-6M para cobertura trimestral, collars estructurados"

- [ ] **[IMP-3]** Ajustar IC width thresholds por horizonte
  - **Archivo:** `chart_interpretations.py:232,236,240`
  - **Actual:** `if avg_ic80_width < 8:` (same for all horizons)
  - **Sugerido:** `threshold_map = {"7d": 8, "15d": 12, "30d": 18, "90d": 25}`
  - **Razón:** IC width naturally expands with longer horizons due to uncertainty

- [ ] **[IMP-4]** Crear tests unitarios para horizon-aware logic
  - **Archivo:** Crear `tests/unit/reporting/test_chart_interpretations.py`
  - **Coverage target:** >80% para funciones `interpret_*()`
  - **Key tests:** Horizon mapping, lookback scaling, framing differences

### 🟢 Nice-to-Have (Could Fix):

- [ ] **[NTH-1]** Extract magic numbers to module-level constants
  - **Archivo:** `chart_interpretations.py` - top of module
  - **Crear:** `HORIZON_PARAMS` dict con todos los thresholds/lookbacks
  - **Beneficio:** Más mantenible, autoconfigurable, fácil tuning

- [ ] **[NTH-2]** Consolidar trend determination logic en helper function
  - **Archivo:** `chart_interpretations.py` (nueva función `_determine_trend_bias()`)
  - **Reemplazar:** Lógica duplicada en líneas 60-79, 251-260, 527-535
  - **Beneficio:** DRY, consistencia

- [ ] **[NTH-3]** Agregar input validation para `horizon` parameter
  - **Archivo:** Todas las funciones `interpret_*()`
  - **Validación:** `if horizon not in VALID_HORIZONS: horizon = "7d"`
  - **Beneficio:** Fail gracefully, mejor developer experience

- [ ] **[NTH-4]** Add type hints para return types de helpers
  - **Archivo:** `chart_interpretations.py:476-510`
  - **Ejemplo:** `def extract_correlation_metrics(bundle: DataBundle) -> Dict[str, float]:`
  - **Beneficio:** Mejor IDE support, type safety

---

## 💡 Sugerencias Adicionales

### Refactoring Oportunidades:

1. **Crear `HorizonConfig` dataclass para centralizar parámetros**
   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class HorizonConfig:
       """Configuration for horizon-specific interpretation parameters."""
       code: str  # "7d", "15d", etc.
       projection_days: int
       hist_context_days: int
       tactical_zoom_days: int
       ic80_low_threshold: float
       ic80_moderate_threshold: float
       ic80_high_threshold: float
       timeframe_label: str  # "próxima semana", "próximo mes", etc.
       trading_style: str  # "táctico", "corto plazo", "medio plazo", "estratégico"
       instruments: List[str]
       scenario_focus: str

   HORIZON_CONFIGS = {
       "7d": HorizonConfig(
           code="7d",
           projection_days=7,
           hist_context_days=30,
           tactical_zoom_days=5,
           ic80_low_threshold=8.0,
           ic80_moderate_threshold=12.0,
           ic80_high_threshold=18.0,
           timeframe_label="próxima semana",
           trading_style="táctico (1-5 días)",
           instruments=["opciones semanales", "spot", "forwards overnight"],
           scenario_focus="niveles técnicos específicos y triggers corto plazo",
       ),
       # ... 15d, 30d, 90d configs
   }
   ```

   **Beneficio:** Single source of truth, type-safe, fácil agregar nuevos horizontes

2. **Consider Strategy Pattern para horizon-specific interpretations**

   Si las interpretaciones divergen mucho por horizonte, considerar:
   ```python
   class InterpretationStrategy(ABC):
       @abstractmethod
       def interpret_hist_overview(self, bundle, forecast) -> str: ...

       @abstractmethod
       def interpret_tactical_zoom(self, bundle, forecast) -> str: ...

   class TacticalInterpreter(InterpretationStrategy):
       """For 7d horizon - day-trading focused."""
       # ... implements tactical logic

   class StrategicInterpreter(InterpretationStrategy):
       """For 90d horizon - strategic planning focused."""
       # ... implements strategic logic

   INTERPRETER_MAP = {
       "7d": TacticalInterpreter(),
       "15d": ShortTermInterpreter(),
       "30d": MediumTermInterpreter(),
       "90d": StrategicInterpreter(),
   }
   ```

   **Pro:** Clean separation, extensible
   **Con:** More complex, might be overkill if interpretations share 80% of logic
   **Recomendación:** Esperar a ver cuánto divergen las interpretaciones antes de implementar

---

## 📚 Referencias y Recursos

**Estándares violados:**
- **DRY (Don't Repeat Yourself)**: Trend determination logic duplicada en 3 funciones
- **YAGNI (You Aren't Gonna Need It)**: No aplica - las funcionalidades horizon-aware SÍ se necesitan
- **SOLID - Single Responsibility**: Funciones hacen múltiples cosas (extract data, calculate, format) - podría mejorarse con helpers

**Documentación relevante:**
- Forex core constants: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/config/constants.py`
- Service configs: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_*/config.py`
- Original 7d implementation (working reference): `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/`

**Similar Issues:**
- Este es el primer multi-horizon implementation - no hay PRs/issues previos
- Similar pattern podría afectar 12m forecaster si usa misma arquitectura

---

## 🏁 Conclusión y Siguiente Paso

### Resumen:

El sistema de interpretaciones multi-horizonte tiene una **falla arquitectural crítica**: los service configs retornan `horizon="daily"` para todos los horizontes, causando que las funciones de interpretación generen contenido genérico en vez de horizon-specific insights.

Adicionalmente, las funciones de interpretación tienen **hardcoded lookback periods y scenario framing** que no se ajustan según el horizonte del forecast. Un reporte de 90 días recibe el mismo análisis táctico que un reporte de 7 días, lo cual es inadecuado para usuarios que necesitan perspectivas estratégicas.

### Root Cause Analysis:

1. **Config Layer Bug**: `horizon: Literal["daily"] = "daily"` en todos los service configs (15d, 30d, 90d)
2. **Missing Abstraction**: No existe un `horizon_code` o `horizon_label` separado del `horizon_type` (daily vs monthly)
3. **Hardcoded Assumptions**: Interpretations assume tactical 7d horizon (5d zoom, 30d context, day-trading advice)
4. **No Horizon Scaling**: Thresholds, lookbacks, y scenario framing no escalan con forecast horizon

### Impacto en Usuario:

- CFO buscando forecast de 90 días para planificación trimestral recibe consejos de "stops ajustados 0.8%" y "sizing 1.5x" - day-trading advice inapropiado
- Reportes de 30d/90d muestran "Contexto 30d" (demasiado corto) y "Zoom últimos 5d" (demasiado táctico)
- Todos los reportes tienen texto casi idéntico en vez de insights diferenciados por horizonte

### Fix Recomendado:

**Fase 1 - Critical Fixes (2-3 horas):**
1. Agregar `horizon_code` property a service configs (15d, 30d, 90d)
2. Actualizar pipelines para pasar `horizon_code` en vez de `horizon`
3. Implementar horizon-aware lookback maps en `interpret_hist_overview()` y `interpret_tactical_zoom()`

**Fase 2 - Important Improvements (4-5 horas):**
4. Implementar `_get_horizon_framing()` utility con trading styles por horizonte
5. Ajustar volatility sizing advice y IC thresholds por horizonte
6. Crear tests unitarios para validar horizon-specific behavior

**Fase 3 - Nice-to-Haves (2-3 horas):**
7. Extract magic numbers a `HORIZON_PARAMS` constant
8. Consolidar trend determination logic en helper
9. Add input validation y type hints

**Decisión:** REQUEST CHANGES

**Tiempo estimado para fixes:** 8-11 horas (Fase 1+2), 10-14 horas (completo)

**Requiere re-review después de fixes:** Sí - Re-review critical changes (Fase 1) antes de deploy

---

**📝 Generado por:** Code Reviewer Agent
**🤖 Claude Code (Sonnet 4.5)**
**⏱️ Tiempo de review:** ~25 minutos
**📍 Working directory:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system`
