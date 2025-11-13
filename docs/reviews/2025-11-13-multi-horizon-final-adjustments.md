# Multi-Horizon USD/CLP System - Final Adjustments Implementation Plan

**Date:** 2025-11-13
**Reviewer:** Code Reviewer Agent
**Status:** Ready for Implementation

---

## EXECUTIVE SUMMARY

**Scope:** Complete horizon-specific implementation for charts, emails, and cron schedules.

**Status:**
- ✅ COMPLETED: Horizon-specific interpretations (chart_interpretations.py)
- ✅ COMPLETED: Service configs with horizon_code property
- ✅ COMPLETED: Pipelines passing horizon_code to generators
- 🔴 REMAINING: Charts with hardcoded lookback periods
- 🔴 REMAINING: Email templates without executive summaries
- 🔴 REMAINING: 7d crontab running daily instead of weekly

**Estimated Implementation Time:** 2-3 hours

---

## SECTION 1: CHART MODIFICATIONS (CRITICAL)

### 1.1 Overview of Issues

**File:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/charting.py`

**Critical hardcoded values found:**

| Line | Current Code | Issue | Horizon Impact |
|------|-------------|-------|----------------|
| 149 | `hist = bundle.usdclp_series.tail(30)` | Fixed 30 days for ALL horizons | 7d gets 30d context, 90d gets same 30d (should be 180d) |
| 388 | `frame = technicals["frame"].tail(60)` | Fixed 60 days for technical chart | Same 60d context for 7d and 90d forecasts |
| 552 | Title: "Matriz de Correlaciones - Retornos Diarios (60 días)" | Hardcoded label | Misleading for different horizons |
| 594 | `lookback = 90` in macro dashboard | Fixed 90 days | Same context for all horizons |
| 720 | `lookback = 30` in regime chart | Fixed 30 days | Same regime window for all horizons |

### 1.2 Solution: Horizon-Aware Lookback Maps

**Add to charting.py after imports (line 32):**

```python
# Horizon-specific lookback periods for historical context in charts
CHART_HIST_LOOKBACK = {
    "7d": 30,     # Last 30 days of history for weekly forecast
    "15d": 60,    # Last 60 days for bi-weekly forecast
    "30d": 90,    # Last 90 days (3 months) for monthly forecast
    "90d": 180,   # Last 180 days (6 months) for quarterly forecast
    "12m": 365,   # Last 365 days (1 year) for annual forecast
}

# Horizon-specific lookback for technical indicators chart
CHART_TECH_LOOKBACK = {
    "7d": 60,     # 60 days of technicals for 7d forecast
    "15d": 90,    # 90 days for 15d forecast
    "30d": 120,   # 120 days (4 months) for 30d forecast
    "90d": 240,   # 240 days (8 months) for 90d forecast
    "12m": 365,   # 365 days for 12m forecast
}

# Horizon-specific lookback for macro dashboard
CHART_MACRO_LOOKBACK = {
    "7d": 90,     # 90 days of macro context
    "15d": 120,   # 120 days
    "30d": 180,   # 180 days (6 months)
    "90d": 365,   # 365 days (1 year)
    "12m": 730,   # 730 days (2 years)
}

# Horizon-specific lookback for risk regime chart
CHART_REGIME_LOOKBACK = {
    "7d": 30,     # 30 days for short-term regime
    "15d": 45,    # 45 days
    "30d": 60,    # 60 days (2 months)
    "90d": 90,    # 90 days (3 months)
    "12m": 180,   # 180 days (6 months)
}
```

### 1.3 Specific Code Changes

#### Change 1: Historical Overview Chart (Line 149)

**Location:** `_generate_hist_forecast_overview()` method

**Current code (line 148-149):**
```python
# Get last 30 days of historical data
hist = bundle.usdclp_series.tail(30)
```

**Replace with:**
```python
# Get horizon-specific historical context
lookback_days = CHART_HIST_LOOKBACK.get(horizon, 30)
hist = bundle.usdclp_series.tail(lookback_days)
```

**Also update line 167:**
```python
# CURRENT:
ax.plot(hist.index, hist.values, label="Histórico 30d", color="#1f77b4", linewidth=2)

# REPLACE WITH:
ax.plot(hist.index, hist.values, label=f"Histórico {lookback_days}d", color="#1f77b4", linewidth=2)
```

---

#### Change 2: Technical Indicators Panel (Line 388)

**Location:** `_generate_technical_panel()` method

**Current code (line 387-388):**
```python
# Compute technical indicators
technicals = compute_technicals(bundle.usdclp_series)
frame = technicals["frame"].tail(60)  # Last 60 periods
```

**Replace with:**
```python
# Compute technical indicators
technicals = compute_technicals(bundle.usdclp_series)
lookback_days = CHART_TECH_LOOKBACK.get(horizon, 60)
frame = technicals["frame"].tail(lookback_days)
```

**Also update title (line 406):**
```python
# CURRENT:
ax1.set_title("Análisis Técnico USD/CLP (60 días)", fontsize=13, fontweight="bold")

# REPLACE WITH:
ax1.set_title(f"Análisis Técnico USD/CLP ({lookback_days} días)", fontsize=13, fontweight="bold")
```

---

#### Change 3: Correlation Matrix Title (Line 552)

**Location:** `_generate_correlation_matrix()` method

**Current code (line 551-556):**
```python
ax.set_title(
    "Matriz de Correlaciones - Retornos Diarios (60 días)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
```

**Replace with:**
```python
# Use same lookback as technical chart for consistency
lookback_days = CHART_TECH_LOOKBACK.get(horizon, 60)
ax.set_title(
    f"Matriz de Correlaciones - Retornos Diarios ({lookback_days} días)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
```

---

#### Change 4: Macro Dashboard (Line 594)

**Location:** `_generate_macro_dashboard()` method

**Current code (line 593-594):**
```python
# Get last 90 days
lookback = 90
```

**Replace with:**
```python
# Get horizon-specific macro context
lookback = CHART_MACRO_LOOKBACK.get(horizon, 90)
```

---

#### Change 5: Risk Regime Chart (Line 720)

**Location:** `_generate_regime_chart()` method

**Current code (line 719-720):**
```python
# Get recent data (30 days)
lookback = 30
```

**Replace with:**
```python
# Get horizon-specific regime window
lookback = CHART_REGIME_LOOKBACK.get(horizon, 30)
```

**Also update title (line 810):**
```python
# CURRENT:
fig.suptitle("Régimen de Riesgo de Mercado (5 días)", fontsize=16, fontweight="bold")

# REPLACE WITH:
fig.suptitle(f"Régimen de Riesgo de Mercado ({lookback} días)", fontsize=16, fontweight="bold")
```

---

### 1.4 Chart Modifications Summary Table

| Chart Function | Current Lookback | New Lookback Source | Lines to Modify |
|----------------|------------------|---------------------|-----------------|
| `_generate_hist_forecast_overview()` | 30 (hardcoded) | `CHART_HIST_LOOKBACK[horizon]` | 149, 167 |
| `_generate_technical_panel()` | 60 (hardcoded) | `CHART_TECH_LOOKBACK[horizon]` | 388, 406 |
| `_generate_correlation_matrix()` | 60 (implied in title) | `CHART_TECH_LOOKBACK[horizon]` | 552 |
| `_generate_macro_dashboard()` | 90 (hardcoded) | `CHART_MACRO_LOOKBACK[horizon]` | 594 |
| `_generate_regime_chart()` | 30 (hardcoded) | `CHART_REGIME_LOOKBACK[horizon]` | 720, 810 |

---

## SECTION 2: EMAIL TEMPLATE MODIFICATIONS (CRITICAL)

### 2.1 Current Email Implementation

**File:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/notifications/email.py`

**Current subject generation (lines 174-193):**
```python
def _generate_subject(self, report_path: Path) -> str:
    filename = report_path.stem

    if "7d" in filename:
        return "Proyección USD/CLP (7 días) - Forex Forecast System"
    elif "12m" in filename:
        return "Proyección USD/CLP (12 meses) - Forex Forecast System"
    elif "importer" in filename.lower():
        return "Informe Entorno Importador - Forex Forecast System"
    else:
        return "Reporte USD/CLP - Forex Forecast System"
```

**Current body generation (lines 195-218):**
```python
def _generate_body(self, report_path: Path) -> str:
    body = (
        "Estimado/a,\n\n"
        "Se adjunta el reporte de proyección USD/CLP generado automáticamente.\n\n"
        f"Archivo: {report_path.name}\n"
        f"Tamaño: {report_path.stat().st_size / 1024:.1f} KB\n\n"
        "Este reporte ha sido generado mediante modelos estadísticos (ARIMA, VAR, Random Forest) "
        "con datos actualizados del Banco Central de Chile, Federal Reserve, y otras fuentes.\n\n"
        "Para consultas o soporte técnico, responder a este correo.\n\n"
        "Saludos,\n"
        "Forex Forecast System\n"
        "🤖 Generado automáticamente"
    )
    return body
```

### 2.2 Issues with Current Implementation

1. **No Executive Summary:** Email body lacks forecast highlights (bias, range, actions)
2. **No Horizon-Specific Actions:** Same generic text for all horizons
3. **Subject doesn't include DATE or BIAS:** Missing critical info for inbox scanning
4. **No forecast data access:** Methods don't receive forecast results

### 2.3 Solution: Enhanced Email with Executive Summary

**Approach:**
- Modify `EmailSender.send()` to accept optional `forecast` and `bundle` parameters
- Create new method `_generate_executive_summary()` that extracts forecast metrics
- Update `_generate_subject()` to include date and bias
- Update `_generate_body()` to include executive summary

### 2.4 Required Code Changes to email.py

#### Change 1: Update EmailSender.send() signature (line 80-86)

**Current:**
```python
def send(
    self,
    report_path: Path,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    additional_attachments: Sequence[Path] = None,
) -> None:
```

**Replace with:**
```python
def send(
    self,
    report_path: Path,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    additional_attachments: Sequence[Path] = None,
    forecast: Optional[Any] = None,  # ForecastResult for executive summary
    bundle: Optional[Any] = None,    # DataBundle for current price
    horizon: str = "7d",             # Horizon code for labels
) -> None:
```

**Add type import at top of file (line 24):**
```python
from typing import List, Sequence, Optional, Any
```

---

#### Change 2: Update auto-generation logic (lines 103-109)

**Current:**
```python
# Auto-generate subject if not provided
if subject is None:
    subject = self._generate_subject(report_path)

# Auto-generate body if not provided
if body is None:
    body = self._generate_body(report_path)
```

**Replace with:**
```python
# Auto-generate subject if not provided
if subject is None:
    subject = self._generate_subject(report_path, forecast, bundle, horizon)

# Auto-generate body if not provided
if body is None:
    body = self._generate_body(report_path, forecast, bundle, horizon)
```

---

#### Change 3: Add new _generate_executive_summary() method (insert after line 173)

```python
def _generate_executive_summary(
    self,
    forecast: Any,
    bundle: Any,
    horizon: str,
) -> str:
    """
    Generate executive summary from forecast results.

    Args:
        forecast: ForecastResult with predictions
        bundle: DataBundle with current price
        horizon: Horizon code (e.g., "7d", "15d", "30d", "90d")

    Returns:
        Formatted executive summary string
    """
    if forecast is None or bundle is None:
        return ""

    # Horizon labels
    horizon_labels = {
        "7d": "Semanal (7 días)",
        "15d": "Quincenal (15 días)",
        "30d": "Mensual (30 días)",
        "90d": "Trimestral (90 días)",
        "12m": "Anual (12 meses)",
    }
    horizon_label = horizon_labels.get(horizon, f"Horizonte {horizon}")

    # Extract forecast data
    current_price = float(bundle.usdclp_series.iloc[-1])
    fc_last = forecast.series[-1]
    fc_mean = fc_last.mean
    fc_low = fc_last.ci80_low
    fc_high = fc_last.ci80_high

    # Calculate directional bias
    price_change_pct = ((fc_mean / current_price) - 1) * 100

    if price_change_pct > 0.5:
        bias = "ALCISTA (Bullish)"
        bias_emoji = "📈"
    elif price_change_pct < -0.5:
        bias = "BAJISTA (Bearish)"
        bias_emoji = "📉"
    else:
        bias = "NEUTRAL (Range-bound)"
        bias_emoji = "↔️"

    # Horizon-specific actions
    if horizon == "7d":
        if price_change_pct > 0.5:
            action_importers = "Cubrir 30-50% exposición esta semana, stops en ruptura IC 95%"
            action_exporters = "Esperar retrocesos, setup corto en resistencias"
            action_traders = "Long USD/CLP en pullbacks a IC 80% inferior, target banda superior"
        elif price_change_pct < -0.5:
            action_importers = "Aguardar niveles más bajos, no apurar coberturas"
            action_exporters = "Asegurar ventas en niveles actuales, protección contra caída"
            action_traders = "Short USD/CLP en rebotes a IC 80% superior, target banda inferior"
        else:
            action_importers = "Estrategia gradual 20% semanal, vender volatilidad"
            action_exporters = "Estrategia gradual 20% semanal, vender volatilidad"
            action_traders = "Range-trading: comprar soporte, vender resistencia, theta farming"

    elif horizon == "15d":
        if price_change_pct > 0.5:
            action_importers = "Cubrir 50-70% exposición en 2 semanas, entrada escalonada"
            action_exporters = "Evitar nuevos compromisos CLP, renegociar plazos si posible"
            action_traders = "Posición alcista core, reducir en zona IC 80% superior"
        elif price_change_pct < -0.5:
            action_importers = "Postponer coberturas, esperar soporte IC 80%"
            action_exporters = "Maximizar ventas USD, cobertura agresiva 70-80%"
            action_traders = "Posición bajista core, tomar ganancias en IC 80% inferior"
        else:
            action_importers = "Cobertura 40-50% gradual, mantener flexibilidad"
            action_exporters = "Cobertura 40-50% gradual, mantener flexibilidad"
            action_traders = "Estrategia neutral: iron condor, aprovechar time decay"

    elif horizon == "30d":
        if price_change_pct > 0.5:
            action_importers = "Cobertura completa 80-100% escalonada mensual"
            action_exporters = "Minimizar exposición CLP, cobertura defensiva"
            action_traders = "Posición alcista estratégica, stops amplios IC 95%"
        elif price_change_pct < -0.5:
            action_importers = "Estrategia wait-and-see, aprovechar fortaleza CLP"
            action_exporters = "Cobertura agresiva 90-100%, locks en niveles favorables"
            action_traders = "Posición bajista estratégica, profit-taking escalonado"
        else:
            action_importers = "Cobertura 50-60% del mes, monitorear drivers macro"
            action_exporters = "Cobertura 50-60% del mes, monitorear drivers macro"
            action_traders = "Strategies multi-leg, aprovechar rango proyectado"

    elif horizon == "90d":
        if price_change_pct > 0.5:
            action_importers = "Cobertura forward completa trimestre, considerar opciones cap"
            action_exporters = "Exposición mínima CLP, renegociar contratos a USD"
            action_traders = "Posición direccional con cobertura tail-risk (put spread)"
        elif price_change_pct < -0.5:
            action_importers = "Estrategia spot/forward mix, aprovechar forward points"
            action_exporters = "Cobertura máxima, explorar estructuras participativas"
            action_traders = "Posición direccional bajista, hedge con call spread"
        else:
            action_importers = "Cobertura 60-70% con collar options, flexibilidad táctica"
            action_exporters = "Cobertura 60-70% con collar options, flexibilidad táctica"
            action_traders = "Portfolio multi-estrategia: direccional + vol + carry"

    else:  # 12m or other
        action_importers = "Consultar estrategia de cobertura con tesorería"
        action_exporters = "Consultar estrategia de cobertura con tesorería"
        action_traders = "Estrategia de largo plazo caso por caso"

    # Build executive summary
    summary = (
        f"\n=== RESUMEN EJECUTIVO ===\n"
        f"Período analizado: {horizon_label}\n"
        f"Sesgo direccional: {bias} {bias_emoji}\n"
        f"Precio actual: {current_price:.2f} CLP\n"
        f"Precio proyectado: {fc_mean:.2f} CLP ({price_change_pct:+.2f}%)\n"
        f"Rango proyectado (IC 80%): {fc_low:.2f} - {fc_high:.2f} CLP\n\n"
        f"ACCIONES RECOMENDADAS:\n"
        f"• [Importadores]: {action_importers}\n"
        f"• [Exportadores]: {action_exporters}\n"
        f"• [Traders]: {action_traders}\n\n"
        f"NOTA: Proyección estadística, no asesoría financiera.\n"
        f"      Validar con análisis fundamental y gestión de riesgos.\n"
        f"=========================\n\n"
    )

    return summary
```

---

#### Change 4: Update _generate_subject() method (lines 174-193)

**Replace entire method:**

```python
def _generate_subject(
    self,
    report_path: Path,
    forecast: Any = None,
    bundle: Any = None,
    horizon: str = "7d",
) -> str:
    """
    Generate email subject with date, horizon, and bias.

    Format: [USD/CLP] Proyección {HORIZON} - {DATE} - Sesgo {BIAS}

    Args:
        report_path: Path to report file
        forecast: Optional forecast results for bias extraction
        bundle: Optional data bundle for current price
        horizon: Horizon code (e.g., "7d")

    Returns:
        Email subject string
    """
    from datetime import datetime

    # Horizon labels
    horizon_labels = {
        "7d": "7d",
        "15d": "15d",
        "30d": "30d",
        "90d": "90d",
        "12m": "12m",
    }
    horizon_label = horizon_labels.get(horizon, horizon)

    # Date
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Bias (if forecast available)
    bias_str = ""
    if forecast is not None and bundle is not None:
        current_price = float(bundle.usdclp_series.iloc[-1])
        fc_mean = forecast.series[-1].mean
        price_change_pct = ((fc_mean / current_price) - 1) * 100

        if price_change_pct > 0.5:
            bias_str = "ALCISTA 📈"
        elif price_change_pct < -0.5:
            bias_str = "BAJISTA 📉"
        else:
            bias_str = "NEUTRAL ↔️"

    if bias_str:
        return f"[USD/CLP] Proyección {horizon_label} - {date_str} - {bias_str}"
    else:
        return f"[USD/CLP] Proyección {horizon_label} - {date_str}"
```

---

#### Change 5: Update _generate_body() method (lines 195-218)

**Replace entire method:**

```python
def _generate_body(
    self,
    report_path: Path,
    forecast: Any = None,
    bundle: Any = None,
    horizon: str = "7d",
) -> str:
    """
    Generate email body with executive summary.

    Args:
        report_path: Path to report file
        forecast: Optional forecast results
        bundle: Optional data bundle
        horizon: Horizon code

    Returns:
        Email body string
    """
    # Generate executive summary if data available
    exec_summary = self._generate_executive_summary(forecast, bundle, horizon)

    body = (
        f"Estimado/a,\n\n"
        f"Se adjunta el reporte de proyección USD/CLP generado automáticamente.\n"
        f"{exec_summary}"
        f"=== DETALLES DEL ARCHIVO ===\n"
        f"Archivo: {report_path.name}\n"
        f"Tamaño: {report_path.stat().st_size / 1024:.1f} KB\n\n"
        f"Este reporte ha sido generado mediante modelos estadísticos (ARIMA, VAR, Random Forest) "
        f"con datos actualizados del Banco Central de Chile, Federal Reserve, y otras fuentes.\n\n"
        f"=== INFORME COMPLETO ===\n"
        f"Ver PDF adjunto para:\n"
        f"• Gráficos detallados con intervalos de confianza\n"
        f"• Análisis técnico (RSI, MACD, Bollinger Bands)\n"
        f"• Drivers macroeconómicos (Cobre, DXY, TPM, Inflación)\n"
        f"• Matriz de correlaciones y régimen de riesgo\n"
        f"• Interpretaciones profesionales trader-to-trader\n\n"
        f"Para consultas o soporte técnico, responder a este correo.\n\n"
        f"Saludos,\n"
        f"Forex Forecast System\n"
        f"🤖 Generado automáticamente"
    )

    return body
```

---

### 2.5 Update Pipeline to Pass Forecast Data to EmailSender

**Files to modify:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/pipeline.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_15d/pipeline.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_30d/pipeline.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_90d/pipeline.py`

**Change for ALL pipeline files:**

**Current _send_email() function (lines 183-199):**
```python
def _send_email(settings, report_path: Path) -> None:
    """
    Send email notification with report attached.

    NOTE: Email sending is not yet implemented in forex_core.
    This is a placeholder for when EmailSender is available.
    """
    logger.warning("Email sending not yet implemented - placeholder")
    # TODO: Implement when forex_core.notifications.EmailSender is ready
    # from forex_core.notifications import EmailSender
    # sender = EmailSender(settings)
    # sender.send(
    #     subject=f"Proyección USD/CLP 7 días - {datetime.now():%Y-%m-%d}",
    #     body="Se adjunta la proyección de tipo de cambio para los próximos 7 días.",
    #     attachment_path=report_path
    # )
```

**Replace with (adjust horizon for each service: 7d, 15d, 30d, 90d):**

```python
def _send_email(
    settings,
    report_path: Path,
    forecast: ForecastPackage,
    bundle: DataBundle,
    horizon: str,
) -> None:
    """
    Send email notification with report attached including executive summary.

    Args:
        settings: System settings with email configuration
        report_path: Path to generated PDF report
        forecast: Forecast results for executive summary
        bundle: Data bundle for current price context
        horizon: Horizon code (e.g., "7d", "15d", "30d", "90d")
    """
    from forex_core.notifications.email import EmailSender

    try:
        sender = EmailSender(settings)
        sender.send(
            report_path=report_path,
            forecast=forecast,
            bundle=bundle,
            horizon=horizon,
        )
        logger.info(f"Email sent successfully for {horizon} forecast")
    except ValueError as e:
        # Email credentials not configured
        logger.warning(f"Email not sent (credentials not configured): {e}")
    except Exception as e:
        # Other email errors (SMTP, network, etc.)
        logger.error(f"Failed to send email: {e}")
        # Don't raise - email failure shouldn't stop pipeline
```

**Update call to _send_email() in run_forecast_pipeline() (line 106-112):**

**Current:**
```python
# Step 5: Send email (optional)
if not skip_email:
    logger.info("Sending email notification...")
    _send_email(settings, report_path)
    logger.success("Email sent successfully")
else:
    logger.info("Email delivery skipped")
```

**Replace with:**
```python
# Step 5: Send email (optional)
if not skip_email:
    logger.info("Sending email notification...")
    _send_email(settings, report_path, forecast, bundle, service_config.horizon_code)
    logger.success("Email sent successfully")
else:
    logger.info("Email delivery skipped")
```

---

### 2.6 Email Changes Summary

| File | Change | Lines | Description |
|------|--------|-------|-------------|
| `email.py` | Update `send()` signature | 80-86 | Add forecast, bundle, horizon params |
| `email.py` | Add `_generate_executive_summary()` | After 173 | New method for summary generation |
| `email.py` | Replace `_generate_subject()` | 174-193 | Include date and bias in subject |
| `email.py` | Replace `_generate_body()` | 195-218 | Include executive summary in body |
| `forecaster_7d/pipeline.py` | Update `_send_email()` | 183-199 | Implement actual email sending |
| `forecaster_7d/pipeline.py` | Update call to `_send_email()` | 109 | Pass forecast, bundle, horizon |
| `forecaster_15d/pipeline.py` | Update `_send_email()` | 183-199 | Same as 7d |
| `forecaster_15d/pipeline.py` | Update call to `_send_email()` | 109 | Same as 7d |
| `forecaster_30d/pipeline.py` | Update `_send_email()` | 183-199 | Same as 7d |
| `forecaster_30d/pipeline.py` | Update call to `_send_email()` | 109 | Same as 7d |
| `forecaster_90d/pipeline.py` | Update `_send_email()` | 183-199 | Same as 7d |
| `forecaster_90d/pipeline.py` | Update call to `_send_email()` | 109 | Same as 7d |

---

## SECTION 3: CRONTAB UPDATES

### 3.1 Current vs Required Schedules

| Service | Current Schedule | Required Schedule | Status |
|---------|------------------|-------------------|--------|
| 7d | Daily at 08:00 | **Monday at 08:00** | ❌ WRONG |
| 15d | Day 1 and 15 at 09:00 | Day 1 and 15 at 09:00 | ✅ CORRECT |
| 30d | Day 1 at 09:30 | Day 1 at 09:30 | ✅ CORRECT |
| 90d | Day 1 at 10:00 | Day 1 at 10:00 | ✅ CORRECT |

### 3.2 Fix 7d Crontab

**File:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/cron/7d/crontab`

**Current (line 2):**
```cron
0 8 * * * cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1
```

**Replace with:**
```cron
0 8 * * 1 cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1
```

**Explanation:**
- `* * *` = every day
- `* * 1` = only on Monday (day of week 1)

**Cron format reminder:**
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 7, Sunday = 0 or 7)
│ │ │ │ │
0 8 * * 1 = Monday at 08:00
```

### 3.3 Verify Other Crontabs (NO CHANGES NEEDED)

**15d crontab (CORRECT):**
```cron
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1
```
✅ Runs on day 1 and 15 of every month at 09:00

**30d crontab (CORRECT):**
```cron
30 9 1 * * cd /app && python -m services.forecaster_30d.cli run >> /var/log/cron.log 2>&1
```
✅ Runs on day 1 of every month at 09:30

**90d crontab (CORRECT):**
```cron
0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1
```
✅ Runs on day 1 of every month at 10:00

---

## SECTION 4: TESTING CHECKLIST

### 4.1 Pre-Implementation Tests

- [ ] **Backup files before modifying:**
  ```bash
  cp src/forex_core/reporting/charting.py src/forex_core/reporting/charting.py.backup
  cp src/forex_core/notifications/email.py src/forex_core/notifications/email.py.backup
  cp cron/7d/crontab cron/7d/crontab.backup
  ```

- [ ] **Verify current system works:**
  ```bash
  cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
  python -m services.forecaster_7d.cli run --skip-email
  ```

### 4.2 Chart Testing (After Section 1 Implementation)

**Test 7d forecast:**
```bash
python -m services.forecaster_7d.cli run --skip-email
```

**Verify:**
- [ ] Chart `chart_hist_overview_7d.png` shows 30 days of history (label: "Histórico 30d")
- [ ] Chart `chart_technical_panel_7d.png` shows 60 days (title: "Análisis Técnico USD/CLP (60 días)")
- [ ] Chart `chart_correlation_7d.png` title says "(60 días)"
- [ ] Chart `chart_macro_dashboard_7d.png` uses 90 days of data
- [ ] Chart `chart_risk_regime_7d.png` shows 30 days (title: "Régimen de Riesgo de Mercado (30 días)")

**Test 90d forecast:**
```bash
python -m services.forecaster_90d.cli run --skip-email
```

**Verify:**
- [ ] Chart `chart_hist_overview_90d.png` shows 180 days of history (label: "Histórico 180d")
- [ ] Chart `chart_technical_panel_90d.png` shows 240 days (title: "Análisis Técnico USD/CLP (240 días)")
- [ ] Chart `chart_correlation_90d.png` title says "(240 días)"
- [ ] Chart `chart_macro_dashboard_90d.png` uses 365 days of data
- [ ] Chart `chart_risk_regime_90d.png` shows 90 days (title: "Régimen de Riesgo de Mercado (90 días)")

**Compare charts visually:**
- [ ] 7d charts show shorter historical context than 90d charts
- [ ] No visual artifacts or missing data
- [ ] All labels and titles updated correctly

### 4.3 Email Testing (After Section 2 Implementation)

**Test email generation WITHOUT sending (mock test):**

Create test script: `tests/test_email_executive_summary.py`
```python
from pathlib import Path
from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.forecasting import ForecastEngine
from services.forecaster_7d.config import get_service_config
from forex_core.notifications.email import EmailSender

# Load data and generate forecast
settings = get_settings()
service_config = get_service_config()
loader = DataLoader(settings)
bundle = loader.load()

engine = ForecastEngine(
    config=settings,
    horizon=service_config.horizon,
    steps=service_config.steps,
)
forecast, artifacts = engine.forecast(bundle)

# Test email generation (don't actually send)
# Create mock report path
report_path = Path(settings.output_dir) / "reports" / "Forecast_7D_USDCLP_2025-11-13.pdf"

# Create EmailSender (will fail if credentials not set, that's OK for test)
try:
    sender = EmailSender(settings)

    # Test subject generation
    subject = sender._generate_subject(report_path, forecast, bundle, "7d")
    print(f"Subject: {subject}")

    # Test body generation
    body = sender._generate_body(report_path, forecast, bundle, "7d")
    print(f"\nBody:\n{body}")

except ValueError as e:
    print(f"Email credentials not configured (expected): {e}")
    print("\nTesting subject/body generation manually...")

    # Test methods directly (without EmailSender instance)
    from datetime import datetime
    current_price = float(bundle.usdclp_series.iloc[-1])
    fc_mean = forecast.series[-1].mean
    price_change_pct = ((fc_mean / current_price) - 1) * 100

    bias_str = "ALCISTA 📈" if price_change_pct > 0.5 else "BAJISTA 📉" if price_change_pct < -0.5 else "NEUTRAL ↔️"
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"Subject: [USD/CLP] Proyección 7d - {date_str} - {bias_str}")
    print(f"\nPrice change: {price_change_pct:+.2f}%")
    print(f"Bias: {bias_str}")
```

**Run test:**
```bash
python tests/test_email_executive_summary.py
```

**Verify:**
- [ ] Subject format: `[USD/CLP] Proyección 7d - 2025-11-13 - {BIAS}`
- [ ] Body contains "=== RESUMEN EJECUTIVO ==="
- [ ] Body shows current price, projected price, bias
- [ ] Body shows IC 80% range
- [ ] Body contains horizon-specific actions for importers/exporters/traders
- [ ] Body contains "=== INFORME COMPLETO ===" section

**Test with real email sending (if credentials configured):**
```bash
# Set credentials temporarily
export GMAIL_USER="your-email@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export EMAIL_RECIPIENTS="test-recipient@example.com"

# Run 7d forecast with email
python -m services.forecaster_7d.cli run
```

**Verify:**
- [ ] Email received at test recipient
- [ ] Subject includes date and bias
- [ ] Body contains executive summary
- [ ] PDF attached correctly
- [ ] Executive summary matches forecast data

### 4.4 Crontab Testing (After Section 3 Implementation)

**Verify cron syntax:**
```bash
# Check cron syntax validity
crontab -l  # Should not show errors

# Or test specific crontab file
cat cron/7d/crontab | grep -v "^#" | grep -v "^$"
```

**Expected output for 7d:**
```
0 8 * * 1 cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1
0 * * * * date > /tmp/healthcheck
```

**Verify schedule interpretation:**
```bash
# Install cron-descriptor if needed: pip install cron-descriptor
from cron_descriptor import get_description
print(get_description("0 8 * * 1"))  # Should output: "At 08:00 AM, only on Monday"
```

**Manual cron schedule validation:**

| Cron Expression | Service | Expected Behavior |
|-----------------|---------|-------------------|
| `0 8 * * 1` | 7d | Every Monday at 08:00 Chile time |
| `0 9 1,15 * *` | 15d | Day 1 and 15 of every month at 09:00 |
| `30 9 1 * *` | 30d | Day 1 of every month at 09:30 |
| `0 10 1 * *` | 90d | Day 1 of every month at 10:00 |

**Simulate cron run (for testing without waiting):**
```bash
# Run the exact command that cron would execute
cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1

# Or locally (adjust path):
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system && \
  python -m services.forecaster_7d.cli run >> /tmp/cron_test.log 2>&1

# Check log
tail -f /tmp/cron_test.log
```

### 4.5 Integration Testing (Full Pipeline)

**Test all services sequentially:**
```bash
# 7d
python -m services.forecaster_7d.cli run --skip-email
# Verify: charts use 30/60/90/30 day lookbacks

# 15d
python -m services.forecaster_15d.cli run --skip-email
# Verify: charts use 60/90/120/45 day lookbacks

# 30d
python -m services.forecaster_30d.cli run --skip-email
# Verify: charts use 90/120/180/60 day lookbacks

# 90d
python -m services.forecaster_90d.cli run --skip-email
# Verify: charts use 180/240/365/90 day lookbacks
```

**Regression testing:**
- [ ] All charts generate without errors
- [ ] PDF reports build successfully
- [ ] No broken imports or missing dependencies
- [ ] Interpretations still work correctly
- [ ] All horizon-specific language is correct

### 4.6 Edge Case Testing

**Test with missing optional data (e.g., no VIX/EEM data):**
```bash
# Should handle gracefully with fallback messages
python -m services.forecaster_7d.cli run --skip-email
```

**Verify:**
- [ ] Correlation matrix handles missing series
- [ ] Risk regime chart shows "datos insuficientes" message if needed
- [ ] No crashes or exceptions

**Test with extreme forecast values:**
- Manually modify forecast to have wide IC bands (>30 pesos)
- Verify email summary reflects "alta volatilidad"
- Verify position sizing advice adjusts accordingly

### 4.7 Documentation Testing

**Verify all documentation is updated:**
- [ ] README.md mentions horizon-specific charts and emails
- [ ] CHANGELOG.md has entry for v2.4.0 with these changes
- [ ] Service-specific READMEs (if any) are updated

---

## SECTION 5: IMPLEMENTATION ORDER

**Recommended sequence to minimize risk:**

### Step 1: Charts (Lowest Risk)
1. Backup `charting.py`
2. Add lookback maps (Section 1.2)
3. Update all 5 chart methods (Section 1.3)
4. Test with 7d and 90d forecasts (Section 4.2)
5. Verify visually that charts differ appropriately

### Step 2: Crontab (Medium Risk)
1. Backup `cron/7d/crontab`
2. Update line 2 to use `* * 1` (Section 3.2)
3. Verify cron syntax (Section 4.4)
4. Deploy to production (no immediate effect, waits for next Monday)

### Step 3: Email (Highest Risk)
1. Backup `email.py` and all `pipeline.py` files
2. Update `email.py` with new methods (Section 2.4)
3. Update all 4 pipeline files (Section 2.5)
4. Test email generation without sending (Section 4.3)
5. Test with real email if credentials available
6. Deploy to production

**Why this order?**
- Charts are isolated (no external dependencies like SMTP)
- Crontab change only affects scheduling (can be rolled back easily)
- Email touches multiple files and external service (SMTP)

---

## SECTION 6: ROLLBACK PLAN

**If charts break:**
```bash
cp src/forex_core/reporting/charting.py.backup src/forex_core/reporting/charting.py
python -m services.forecaster_7d.cli run --skip-email  # Verify works
```

**If email breaks:**
```bash
cp src/forex_core/notifications/email.py.backup src/forex_core/notifications/email.py
cp src/services/forecaster_7d/pipeline.py.backup src/services/forecaster_7d/pipeline.py
cp src/services/forecaster_15d/pipeline.py.backup src/services/forecaster_15d/pipeline.py
cp src/services/forecaster_30d/pipeline.py.backup src/services/forecaster_30d/pipeline.py
cp src/services/forecaster_90d/pipeline.py.backup src/services/forecaster_90d/pipeline.py
python -m services.forecaster_7d.cli run  # Verify works
```

**If crontab breaks:**
```bash
cp cron/7d/crontab.backup cron/7d/crontab
# Redeploy cron container or reload crontab
```

---

## SECTION 7: FINAL VALIDATION CHECKLIST

### Charts ✅
- [ ] 7d forecast charts use 30/60/90/30 day lookbacks
- [ ] 15d forecast charts use 60/90/120/45 day lookbacks
- [ ] 30d forecast charts use 90/120/180/60 day lookbacks
- [ ] 90d forecast charts use 180/240/365/90 day lookbacks
- [ ] All chart titles/labels reflect correct lookback periods
- [ ] Visual comparison shows appropriate context differences

### Email ✅
- [ ] Subject includes date, horizon, and bias
- [ ] Body contains executive summary with forecast metrics
- [ ] Body shows horizon-specific actions for all user types
- [ ] Executive summary calculations are accurate
- [ ] Email sends successfully (if credentials configured)
- [ ] Email not sent if credentials missing (graceful degradation)

### Crontab ✅
- [ ] 7d runs Monday at 08:00 (not daily)
- [ ] 15d runs day 1 and 15 at 09:00
- [ ] 30d runs day 1 at 09:30
- [ ] 90d runs day 1 at 10:00
- [ ] Healthcheck cron still active

### Integration ✅
- [ ] All services run end-to-end without errors
- [ ] Horizon-specific interpretations still work
- [ ] PDF reports build correctly
- [ ] No regression in existing functionality
- [ ] Logs show correct horizon being used

---

## APPENDIX A: FILES TO MODIFY SUMMARY

| File | Lines to Change | Type | Risk Level |
|------|-----------------|------|------------|
| `src/forex_core/reporting/charting.py` | 32 (add maps), 149, 167, 388, 406, 552, 594, 720, 810 | Charts | LOW |
| `src/forex_core/notifications/email.py` | 24, 80-86, 103-109, 173+ (new method), 174-193, 195-218 | Email | MEDIUM |
| `src/services/forecaster_7d/pipeline.py` | 109, 183-199 | Pipeline | MEDIUM |
| `src/services/forecaster_15d/pipeline.py` | 109, 183-199 | Pipeline | MEDIUM |
| `src/services/forecaster_30d/pipeline.py` | 109, 183-199 | Pipeline | MEDIUM |
| `src/services/forecaster_90d/pipeline.py` | 109, 183-199 | Pipeline | MEDIUM |
| `cron/7d/crontab` | 2 | Schedule | LOW |

**Total files:** 8
**Total lines to modify:** ~50-60 lines
**New code to add:** ~150 lines (executive summary method)

---

## APPENDIX B: HORIZON LOOKBACK REFERENCE TABLE

### Chart Historical Overview (hist_overview)
| Horizon | Lookback | Purpose |
|---------|----------|---------|
| 7d | 30 days | Last month context for weekly forecast |
| 15d | 60 days | Last 2 months context |
| 30d | 90 days | Last quarter context |
| 90d | 180 days | Last semester context |
| 12m | 365 days | Last year context |

### Chart Technical Indicators (technical_panel)
| Horizon | Lookback | Purpose |
|---------|----------|---------|
| 7d | 60 days | 2 months of technicals |
| 15d | 90 days | 3 months of technicals |
| 30d | 120 days | 4 months of technicals |
| 90d | 240 days | 8 months of technicals |
| 12m | 365 days | 1 year of technicals |

### Chart Macro Dashboard (macro_dashboard)
| Horizon | Lookback | Purpose |
|---------|----------|---------|
| 7d | 90 days | Quarter of macro drivers |
| 15d | 120 days | 4 months of macro drivers |
| 30d | 180 days | Semester of macro drivers |
| 90d | 365 days | Year of macro drivers |
| 12m | 730 days | 2 years of macro drivers |

### Chart Risk Regime (risk_regime)
| Horizon | Lookback | Purpose |
|---------|----------|---------|
| 7d | 30 days | Last month regime |
| 15d | 45 days | 1.5 months regime |
| 30d | 60 days | 2 months regime |
| 90d | 90 days | Quarter regime |
| 12m | 180 days | Semester regime |

---

## APPENDIX C: EMAIL EXECUTIVE SUMMARY EXAMPLES

### Example 1: 7d Bullish Forecast
```
Subject: [USD/CLP] Proyección 7d - 2025-11-13 - ALCISTA 📈

Body:
Estimado/a,

Se adjunta el reporte de proyección USD/CLP generado automáticamente.

=== RESUMEN EJECUTIVO ===
Período analizado: Semanal (7 días)
Sesgo direccional: ALCISTA (Bullish) 📈
Precio actual: 938.50 CLP
Precio proyectado: 942.80 CLP (+0.46%)
Rango proyectado (IC 80%): 938.20 - 947.40 CLP

ACCIONES RECOMENDADAS:
• [Importadores]: Cubrir 30-50% exposición esta semana, stops en ruptura IC 95%
• [Exportadores]: Esperar retrocesos, setup corto en resistencias
• [Traders]: Long USD/CLP en pullbacks a IC 80% inferior, target banda superior

NOTA: Proyección estadística, no asesoría financiera.
      Validar con análisis fundamental y gestión de riesgos.
=========================

=== DETALLES DEL ARCHIVO ===
Archivo: Forecast_7D_USDCLP_2025-11-13.pdf
Tamaño: 2847.3 KB

...
```

### Example 2: 30d Neutral Forecast
```
Subject: [USD/CLP] Proyección 30d - 2025-11-13 - NEUTRAL ↔️

Body:
Estimado/a,

Se adjunta el reporte de proyección USD/CLP generado automáticamente.

=== RESUMEN EJECUTIVO ===
Período analizado: Mensual (30 días)
Sesgo direccional: NEUTRAL (Range-bound) ↔️
Precio actual: 935.20 CLP
Precio proyectado: 935.90 CLP (+0.07%)
Rango proyectado (IC 80%): 925.50 - 946.30 CLP

ACCIONES RECOMENDADAS:
• [Importadores]: Cobertura 50-60% del mes, monitorear drivers macro
• [Exportadores]: Cobertura 50-60% del mes, monitorear drivers macro
• [Traders]: Strategies multi-leg, aprovechar rango proyectado

NOTA: Proyección estadística, no asesoría financiera.
      Validar con análisis fundamental y gestión de riesgos.
=========================

...
```

### Example 3: 90d Bearish Forecast
```
Subject: [USD/CLP] Proyección 90d - 2025-11-13 - BAJISTA 📉

Body:
Estimado/a,

Se adjunta el reporte de proyección USD/CLP generado automáticamente.

=== RESUMEN EJECUTIVO ===
Período analizado: Trimestral (90 días)
Sesgo direccional: BAJISTA (Bearish) 📉
Precio actual: 942.10 CLP
Precio proyectado: 928.50 CLP (-1.44%)
Rango proyectado (IC 80%): 915.20 - 941.80 CLP

ACCIONES RECOMENDADAS:
• [Importadores]: Estrategia spot/forward mix, aprovechar forward points
• [Exportadores]: Cobertura máxima, explorar estructuras participativas
• [Traders]: Posición direccional bajista, hedge con call spread

NOTA: Proyección estadística, no asesoría financiera.
      Validar con análisis fundamental y gestión de riesgos.
=========================

...
```

---

## CONCLUSION

This implementation plan provides complete specifications for:
1. Making charts horizon-aware with dynamic lookback periods
2. Adding executive summaries to email notifications
3. Fixing 7d crontab to run weekly instead of daily

All changes are well-defined with exact line numbers, code snippets, and testing procedures. Implementation should take 2-3 hours for an experienced developer, with minimal risk due to the structured approach and rollback plan.

**Next Steps:**
1. Review this plan with team
2. Schedule implementation window
3. Execute in order: Charts → Crontab → Email
4. Validate with testing checklist
5. Deploy to production
6. Monitor first runs for each service

**Generated by:** Code Reviewer Agent
**Claude Code**
**Review Time:** ~45 minutes
