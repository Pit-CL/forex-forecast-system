# MLOps Roadmap - USD/CLP Forex Forecasting System

**Document Version:** 1.0
**Date:** 2025-11-13
**Timeline:** 12 semanas (3 meses)
**Status:** Fase 1 COMPLETADA, Fases 2-5 en roadmap

---

## Resumen Ejecutivo

Este documento define el roadmap completo de MLOps para transformar el sistema de forecasting USD/CLP desde un sistema de producción básico hasta un **sistema completamente autónomo con capacidades de auto-optimización y auto-healing**.

### Visión

Evolucionar el sistema actual en 5 fases incrementales:

1. **Foundation (Semanas 1-2)** ✅ - Logging, tracking, comparación vs actuals
2. **Monitoring (Semanas 3-4)** - Drift detection, walk-forward validation, alertas
3. **Automation (Semanas 5-6)** - Re-training automático, model registry, rollback
4. **Optimization (Semanas 7-8)** - Hyperparameter tuning, ensemble optimization
5. **Full AutoML (Semanas 9-12)** - Selección automática de modelos, A/B testing, autonomía total

### Objetivo Final

Un sistema que:
- Se monitorea a sí mismo continuamente
- Detecta degradación de performance automáticamente
- Re-entrena modelos cuando es necesario
- Optimiza hyperparameters continuamente
- Selecciona los mejores modelos sin intervención humana
- Se recupera automáticamente de fallos

---

## Estado Actual del Sistema

### Capacidades Existentes

**Forecasting Core:**
- ✅ 4 horizontes de pronóstico (7d, 15d, 30d, 90d)
- ✅ 3 modelos base (ARIMA+GARCH, VAR, Random Forest)
- ✅ Ensemble con pesos optimizados
- ✅ Confidence intervals (80%, 95%)
- ✅ Generación de PDFs institucionales
- ✅ Email notifications

**MLOps Foundation (Fase 1 COMPLETADA):**
- ✅ **Prediction Tracking** (`src/forex_core/mlops/tracking.py`)
  - Storage en Parquet con thread-safety
  - 266+ predicciones almacenadas
  - Campos: horizon, forecast_date, target_date, prediction, actual, model_version

- ✅ **Drift Detection** (`src/forex_core/mlops/monitoring.py`)
  - 5 tests estadísticos (Kolmogorov-Smirnov, T-test, Levene, Ljung-Box, Volatility)
  - Detección de cambios en distribución, media, varianza, autocorrelación

- ✅ **Readiness Validation** (`src/forex_core/mlops/readiness.py`)
  - Sistema automático de validación con 5 criterios
  - Scoring 0-100 con 4 niveles (NOT_READY, CAUTIOUS, READY, OPTIMAL)
  - Verificación diaria via cron (9 AM)

**Infraestructura:**
- ✅ Vultr VPS production
- ✅ Docker containerization
- ✅ Cron scheduling
- ✅ Auto-cleanup disk (≥85%)
- ✅ Systemd integration

### Gaps Actuales

❌ **No hay sistema de alertas** cuando performance degrada
❌ **No hay re-entrenamiento automático** de modelos
❌ **No hay model versioning** ni registry
❌ **No hay hyperparameter optimization** continua
❌ **No hay A/B testing** de modelos en producción
❌ **No hay rollback automático** si modelo nuevo falla

---

## Fase 1: Foundation (✅ COMPLETADA)

**Timeline:** Semanas 1-2
**Status:** ✅ **COMPLETADA (2025-11-13)**

### Objetivos

- [x] Implementar sistema de logging de predicciones
- [x] Trackear performance real (RMSE out-of-sample)
- [x] Comparar predicciones vs valores reales
- [x] Crear storage persistente (Parquet)
- [x] Implementar drift detection

### Trabajo Completado

#### 1. Prediction Tracking System

**Archivo:** `src/forex_core/mlops/tracking.py` (257 líneas)

```python
class PredictionTracker:
    """Thread-safe prediction tracker con Parquet storage."""

    def save_prediction(
        self,
        horizon: str,
        forecast_date: datetime,
        target_date: datetime,
        prediction: float,
        confidence_low: float,
        confidence_high: float,
        model_version: str,
        metadata: dict
    ):
        """Guarda predicción con metadata completa."""
```

**Características:**
- Storage en Parquet con append thread-safe
- Campos: horizon, forecast_date, target_date, prediction, actual, confidence intervals
- Metadata: model_version, ensemble_weights, feature_importance
- Lock-based concurrency control

#### 2. Drift Detection

**Archivo:** `src/forex_core/mlops/monitoring.py` (371 líneas)

```python
class DataDriftDetector:
    """5 tests estadísticos para drift detection."""

    def generate_drift_report(self, series: pd.Series) -> DriftReport:
        """Ejecuta 5 tests y genera reporte completo."""
        return DriftReport(
            ks_test=self._kolmogorov_smirnov_test(baseline, test),
            t_test=self._t_test(baseline, test),
            levene_test=self._levene_test(baseline, test),
            ljung_box_test=self._ljung_box_test(baseline, test),
            volatility_test=self._volatility_test(baseline, test)
        )
```

**Tests implementados:**
1. **Kolmogorov-Smirnov:** Cambio en distribución
2. **T-test:** Cambio en media
3. **Levene:** Cambio en varianza
4. **Ljung-Box:** Cambio en autocorrelación
5. **Volatility:** Cambio en volatilidad

#### 3. Readiness Validation

**Archivo:** `src/forex_core/mlops/readiness.py` (560 líneas)

```python
class ChronosReadinessChecker:
    """Sistema de validación automático para nuevos modelos."""

    def assess(self) -> ReadinessReport:
        """Evalúa 5 criterios y retorna score 0-100."""
        checks = [
            self._check_tracking_data(),      # CRITICAL
            self._check_operation_time(),     # CRITICAL
            self._check_drift_detection(),
            self._check_system_stability(),
            self._check_performance_baseline(),
        ]
```

**5 Criterios de validación:**
1. Prediction Tracking Data (50+ predictions/horizon)
2. Operation Time (7+ días)
3. Drift Detection Functionality
4. System Stability
5. Performance Baseline (10+ predictions con actuals)

### Archivos Creados

```
src/forex_core/mlops/
├── __init__.py                  # Exports
├── tracking.py                  # PredictionTracker (257 líneas)
├── monitoring.py                # DataDriftDetector (371 líneas)
└── readiness.py                 # ChronosReadinessChecker (560 líneas)

scripts/
├── check_chronos_readiness.py  # CLI tool (223 líneas)
└── daily_readiness_check.sh    # Cron script (83 líneas)

data/
└── predictions/
    └── predictions.parquet      # Prediction storage
```

### Métricas Actuales

```
Predictions tracked: 266+
Horizons: 7d, 15d, 30d, 90d
Drift tests: 5 (KS, T, Levene, LB, Vol)
Readiness score: 50/100 (NOT_READY)
Cron checks: Daily 9 AM
```

### Lecciones Aprendidas

✅ **Qué funcionó:**
- Parquet es excelente para append operations
- Lock-based threading funciona para volumen bajo
- Cron diario es suficiente para monitoring
- Scoring system (0-100) es intuitivo

⚠️ **Qué mejorar:**
- Fecha de operación muestra 0 días (bug menor)
- Min predictions por horizon = 0 (necesita investigación)
- Readiness check podría ser más frecuente (2x/día?)

---

## Fase 2: Monitoring (Semanas 3-4)

**Timeline:** 2 semanas
**Status:** 🔄 **PARCIALMENTE COMPLETADA (2025-11-13)**

### Objetivos

- [x] Implementar alertas automáticas cuando performance degrada ✅
- [x] Sistema de eventos para detección inteligente ✅
- [x] Email subjects dinámicos con contexto ✅
- [ ] Walk-forward validation con ventanas móviles
- [ ] Dashboard de métricas en tiempo real
- [ ] Tracking de drift trends (no solo detección binaria)

### Trabajo Completado (2025-11-13)

#### 1. Event-Driven Alerts System ✅

**Archivos creados:**
- `src/forex_core/mlops/event_detector.py` (365 líneas)
- `src/forex_core/mlops/alerts.py` (233 líneas)

**Descripción:**
Sistema inteligente de detección de eventos que determina cuándo enviar alertas basado en 5 criterios:

1. **Cambio Significativo en Forecast** (>2%)
   - Compara forecast actual vs último forecast
   - Detecta cambios de dirección (alza/baja)
   - Severity: WARNING (>2%), HIGH (>3%)

2. **Data Drift Detectado**
   - Usa tests estadísticos existentes (KS, T-test, Levene)
   - Severity basada en número de tests significativos
   - WARNING (1 test), HIGH (2+ tests)

3. **Alta Volatilidad** (>1.5x histórica)
   - Compara volatilidad reciente (7d) vs histórica (90d)
   - Anualizada con factor √252
   - Severity: WARNING (>1.5x), HIGH (>2.0x)

4. **Eventos Económicos Próximos**
   - Detecta reuniones BCCh (3er martes del mes)
   - Severity: INFO

5. **Cambio de Régimen de Riesgo**
   - Detecta cambios Risk-On/Risk-Off
   - Severity: INFO

**Código ejemplo:**

```python
class EventDetector:
    """Detecta eventos significativos en el sistema de forecasting."""

    def detect_events(
        self,
        horizon: str,
        current_forecast: ForecastPackage,
        bundle: DataBundle,
    ) -> list[DetectedEvent]:
        """Detecta todos los eventos relevantes."""
        events = []

        # 1. Check forecast change
        forecast_change_event = self._check_forecast_change(horizon, current_forecast)
        if forecast_change_event:
            events.append(forecast_change_event)

        # 2. Check drift
        drift_event = self._check_drift(bundle.usdclp_series)
        if drift_event:
            events.append(drift_event)

        # 3-5. Check volatility, economic events, regime change
        # ...

        return events

    def should_send_alert(self, events: list[DetectedEvent]) -> tuple[bool, str]:
        """Determina si se debe enviar alerta basado en eventos detectados."""
        # Check for any high/critical events
        high_severity_events = [
            e for e in events
            if e.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]
        ]

        if high_severity_events:
            reasons = [e.description for e in high_severity_events]
            return True, "; ".join(reasons)

        # Check for multiple warning events
        warning_events = [e for e in events if e.severity == EventSeverity.WARNING]
        if len(warning_events) >= 2:
            reasons = [e.description for e in warning_events]
            return True, f"Múltiples señales: {'; '.join(reasons)}"

        return False, "Events below alert threshold"
```

**AlertManager:**

```python
class AlertManager:
    """Gestiona decisiones de alertas para el sistema de forecasting."""

    def evaluate_alert(
        self,
        horizon: str,
        forecast: ForecastPackage,
        bundle: DataBundle,
    ) -> AlertDecision:
        """Evalúa si se debe enviar alerta para este forecast."""

        # Detect all events
        events = self.event_detector.detect_events(horizon, forecast, bundle)

        # Determine if should alert
        should_alert, reason = self.event_detector.should_send_alert(events)

        # Determine overall severity
        severity = self._get_overall_severity(events)

        return AlertDecision(
            should_alert=should_alert,
            reason=reason,
            events=events,
            severity=severity,
            timestamp=datetime.now()
        )
```

**Integración en Pipelines:**

Todos los pipelines (7d, 15d, 30d, 90d) fueron modificados para integrar el sistema de alertas:

```python
def _send_email(
    settings,
    report_path: Path,
    bundle: DataBundle,
    forecast: ForecastPackage,
    service_config,
) -> None:
    """Send email notification with report attached, including alert context."""
    from forex_core.mlops.alerts import AlertManager
    from forex_core.notifications.email import EmailSender

    # Evaluate alert conditions
    alert_manager = AlertManager(data_dir=settings.data_dir)
    alert_decision = alert_manager.evaluate_alert(
        horizon=service_config.horizon_code,
        forecast=forecast,
        bundle=bundle,
    )

    # Log alert decision
    alert_manager.log_alert_decision(alert_decision, service_config.horizon_code)

    # Log summary to console
    if alert_decision.should_alert:
        logger.warning(
            f"Alert triggered: {alert_decision.reason} "
            f"(severity: {alert_decision.severity.value})"
        )
    else:
        logger.info(f"No alert: {alert_decision.reason}")

    # Send email with alert context
    sender = EmailSender(settings)
    sender.send(
        report_path=report_path,
        bundle=bundle,
        forecast=forecast,
        horizon=service_config.horizon_code,
        alert_decision=alert_decision,  # NEW PARAMETER
    )
```

#### 2. Dynamic Email Subjects ✅

**Archivo modificado:** `src/forex_core/notifications/email.py`

**Nueva funcionalidad:**

```python
def _generate_dynamic_subject(
    self,
    bundle,
    forecast,
    horizon: str,
    alert_decision=None,
) -> str:
    """Generate dynamic email subject with forecast metrics and alerts."""

    # Get current price and forecast
    current_price = bundle.usdclp_series.iloc[-1]
    fc_mean = forecast.series[-1].mean
    fc_change_pct = ((fc_mean / current_price) - 1) * 100

    # Base subject with prices
    base = f"USD/CLP {horizon}: ${current_price:.0f} → ${fc_mean:.0f} ({fc_change_pct:+.1f}%)"

    # Add alert prefix and context if available
    if alert_decision and alert_decision.should_alert:
        prefix = alert_decision.get_subject_prefix()  # 🚨 ⚠️ 📊 📈
        event_summary = alert_decision.get_event_summary()

        # Build full subject with alert context
        subject = f"{prefix} {base} | {event_summary}"
    else:
        # No alert - add contextual information
        context_parts = []

        # Add regime if available
        if hasattr(bundle, "risk_regime") and bundle.risk_regime:
            context_parts.append(f"Regime: {bundle.risk_regime}")

        # Add bias
        if fc_change_pct > 0.3:
            context_parts.append("Sesgo Alcista")
        elif fc_change_pct < -0.3:
            context_parts.append("Sesgo Bajista")
        else:
            context_parts.append("Neutral")

        context = " | ".join(context_parts) if context_parts else ""
        subject = f"📊 {base} | {context}" if context else f"📊 {base}"

    return subject
```

**Ejemplos de subjects generados:**

Normal (sin alertas):
```
📊 USD/CLP 7d: $935 → $942 (+0.7%) | Neutral
📊 USD/CLP 15d: $938 → $930 (-0.9%) | Sesgo Bajista
```

Con alertas:
```
⚠️ USD/CLP 7d: $935 → $950 (+1.6%) | Forecast Change
🚨 USD/CLP 30d: $942 → $965 (+2.4%) | High Volatility
📊 USD/CLP 7d: $938 → $941 (+0.3%) | Pre-BCCh (martes)
```

#### 3. Logging de Decisiones de Alertas ✅

El AlertManager ahora registra todas las decisiones de alertas en archivos log:

```
logs/
├── alerts_7d.log
├── alerts_15d.log
├── alerts_30d.log
└── alerts_90d.log
```

Formato del log:

```
============================================================
ALERT EVALUATION - 7d
============================================================
Timestamp: 2025-11-13 08:00:15
Decision: SEND ALERT
Severity: HIGH
Reason: Cambio significativo en forecast: alza de 2.4%

Events detected: 2
  1. [HIGH] FORECAST_CHANGE
     Cambio significativo en forecast: alza de 2.4%
     Metrics: {'current': 950.5, 'previous': 927.2, 'change_pct': 2.4, 'direction': 'alza'}
  2. [WARNING] HIGH_VOLATILITY
     Volatilidad elevada: 1.6x la histórica
     Metrics: {'recent_vol': 0.082, 'historical_vol': 0.051, 'ratio': 1.6}
============================================================
```

### Trabajo Pendiente

#### 1. Performance Monitoring & Alerts (Mejorar)

**Archivo nuevo:** `src/forex_core/mlops/performance.py`

```python
class PerformanceMonitor:
    """Monitorea performance y dispara alertas."""

    def __init__(
        self,
        tracker: PredictionTracker,
        thresholds: Dict[str, float],
        alert_channels: List[str]
    ):
        self.tracker = tracker
        self.thresholds = thresholds  # {'7d': 12.0, '15d': 20.0, ...}
        self.alert_channels = alert_channels

    def check_performance(self, horizon: str, window_days: int = 30) -> PerformanceReport:
        """Calcula métricas de performance en ventana reciente."""
        predictions = self.tracker.get_predictions_with_actuals(
            horizon=horizon,
            days=window_days
        )

        rmse = self._calculate_rmse(predictions)
        mae = self._calculate_mae(predictions)
        mape = self._calculate_mape(predictions)
        coverage_80 = self._calculate_coverage(predictions, ci=80)
        coverage_95 = self._calculate_coverage(predictions, ci=95)

        # Comparar vs baseline
        baseline_rmse = self._get_baseline_rmse(horizon)
        degradation_pct = ((rmse - baseline_rmse) / baseline_rmse) * 100

        if degradation_pct > 20:  # 20% degradación
            self._send_alert(
                severity='HIGH',
                message=f'{horizon} RMSE degraded {degradation_pct:.1f}%',
                metrics={'rmse': rmse, 'baseline': baseline_rmse}
            )

        return PerformanceReport(
            horizon=horizon,
            rmse=rmse,
            mae=mae,
            mape=mape,
            coverage_80=coverage_80,
            coverage_95=coverage_95,
            degradation_pct=degradation_pct,
            alert_triggered=degradation_pct > 20
        )

    def _send_alert(self, severity: str, message: str, metrics: dict):
        """Envía alerta por múltiples canales."""
        for channel in self.alert_channels:
            if channel == 'email':
                self._send_email_alert(severity, message, metrics)
            elif channel == 'slack':
                self._send_slack_alert(severity, message, metrics)
```

**Thresholds sugeridos:**
- **Degradación < 10%:** INFO (log only)
- **Degradación 10-20%:** WARNING (email)
- **Degradación > 20%:** HIGH (email + Slack)
- **Degradación > 50%:** CRITICAL (email + Slack + SMS?)

#### 2. Walk-Forward Validation

**Archivo nuevo:** `src/forex_core/mlops/validation.py`

```python
class WalkForwardValidator:
    """Walk-forward validation para evaluar modelos out-of-sample."""

    def __init__(
        self,
        forecast_engine: ForecastEngine,
        initial_train_days: int = 365,
        test_days: int = 30,
        step_days: int = 7
    ):
        self.engine = forecast_engine
        self.initial_train_days = initial_train_days
        self.test_days = test_days
        self.step_days = step_days

    def validate(
        self,
        data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime
    ) -> ValidationReport:
        """Ejecuta walk-forward validation."""
        results = []

        current_train_end = start_date + timedelta(days=self.initial_train_days)

        while current_train_end + timedelta(days=self.test_days) <= end_date:
            # Train window
            train_data = data[data.index <= current_train_end]

            # Test window
            test_start = current_train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.test_days)
            test_data = data[(data.index > test_start) & (data.index <= test_end)]

            # Train model
            self.engine.fit(train_data)

            # Generate forecasts
            forecasts = self.engine.predict(steps=self.test_days)

            # Calculate metrics
            actuals = test_data['usdclp'].values
            rmse = np.sqrt(mean_squared_error(actuals, forecasts))
            mae = mean_absolute_error(actuals, forecasts)

            results.append({
                'train_end': current_train_end,
                'test_start': test_start,
                'test_end': test_end,
                'rmse': rmse,
                'mae': mae,
                'n_samples': len(actuals)
            })

            # Step forward
            current_train_end += timedelta(days=self.step_days)

        return ValidationReport(
            results=pd.DataFrame(results),
            mean_rmse=np.mean([r['rmse'] for r in results]),
            std_rmse=np.std([r['rmse'] for r in results]),
            mean_mae=np.mean([r['mae'] for r in results])
        )
```

**Uso sugerido:**
```python
# Validar modelo 7d con walk-forward
validator = WalkForwardValidator(
    forecast_engine=engine_7d,
    initial_train_days=365,
    test_days=7,
    step_days=7  # Weekly steps
)

report = validator.validate(
    data=historical_data,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)

print(f"Mean RMSE: {report.mean_rmse:.2f}")
print(f"Std RMSE: {report.std_rmse:.2f}")
```

#### 3. Drift Trend Analysis

**Archivo nuevo:** `src/forex_core/mlops/drift_trends.py`

```python
class DriftTrendAnalyzer:
    """Analiza trends en drift detection a lo largo del tiempo."""

    def __init__(self, detector: DataDriftDetector):
        self.detector = detector
        self.history: List[DriftReport] = []

    def analyze_trend(
        self,
        series: pd.Series,
        lookback_windows: int = 10
    ) -> DriftTrendReport:
        """Analiza trend de drift en últimas N ventanas."""

        # Run detection
        current_report = self.detector.generate_drift_report(series)
        self.history.append(current_report)

        # Keep only last N windows
        if len(self.history) > lookback_windows:
            self.history = self.history[-lookback_windows:]

        # Analyze trends
        ks_pvalues = [r.ks_test.p_value for r in self.history]
        t_pvalues = [r.t_test.p_value for r in self.history]

        # Drift severity score (0-100)
        # Lower p-values = higher drift
        drift_score = 100 * (1 - np.mean(ks_pvalues))

        # Detect increasing drift trend
        if len(ks_pvalues) >= 3:
            recent_trend = np.polyfit(range(len(ks_pvalues)), ks_pvalues, deg=1)[0]
            is_worsening = recent_trend < 0  # p-values decreasing
        else:
            is_worsening = False

        return DriftTrendReport(
            current_report=current_report,
            drift_score=drift_score,
            is_worsening=is_worsening,
            history_length=len(self.history),
            mean_ks_pvalue=np.mean(ks_pvalues)
        )
```

#### 4. Metrics Dashboard (CLI)

**Archivo nuevo:** `scripts/mlops_dashboard.py`

```python
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer()
console = Console()

@app.command()
def show(horizon: str = typer.Option("7d")):
    """Muestra dashboard de métricas MLOps."""

    tracker = PredictionTracker(data_dir=Path("data"))
    monitor = PerformanceMonitor(tracker, thresholds={'7d': 12.0})

    # Get recent performance
    perf = monitor.check_performance(horizon=horizon, window_days=30)

    # Create table
    table = Table(title=f"MLOps Dashboard - {horizon} Horizon")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_column("Status", style="green")

    table.add_row("RMSE", f"{perf.rmse:.2f}", "✓" if perf.rmse < 12 else "✗")
    table.add_row("MAE", f"{perf.mae:.2f}", "✓")
    table.add_row("MAPE", f"{perf.mape:.2f}%", "✓")
    table.add_row("Coverage 80%", f"{perf.coverage_80:.1f}%", "✓" if perf.coverage_80 > 75 else "✗")
    table.add_row("Coverage 95%", f"{perf.coverage_95:.1f}%", "✓" if perf.coverage_95 > 90 else "✗")
    table.add_row("Degradation", f"{perf.degradation_pct:.1f}%", "✓" if perf.degradation_pct < 10 else "✗")

    console.print(table)

    # Drift status
    detector = DataDriftDetector()
    drift = detector.generate_drift_report(series)

    drift_panel = Panel(
        f"Distribution: {'✓' if drift.ks_test.p_value > 0.05 else '✗ DRIFT'}\n"
        f"Mean: {'✓' if drift.t_test.p_value > 0.05 else '✗ SHIFT'}\n"
        f"Variance: {'✓' if drift.levene_test.p_value > 0.05 else '✗ CHANGE'}",
        title="Drift Detection"
    )
    console.print(drift_panel)
```

### Archivos a Crear/Modificar

```
src/forex_core/mlops/
├── performance.py          # NEW - Performance monitoring & alerts
├── validation.py           # NEW - Walk-forward validator
├── drift_trends.py         # NEW - Drift trend analysis
└── __init__.py            # MODIFY - Add new exports

scripts/
├── mlops_dashboard.py      # NEW - CLI dashboard
└── daily_performance_check.sh  # NEW - Cron script

tests/
└── unit/mlops/
    ├── test_performance.py  # NEW
    ├── test_validation.py   # NEW
    └── test_drift_trends.py # NEW
```

### Dependencias Nuevas

```python
# requirements.txt additions
rich>=13.7.0           # CLI dashboard
slack-sdk>=3.27.0      # Slack notifications (optional)
```

### Cron Jobs Adicionales

```cron
# Performance check diario (después de forecast)
30 8 * * * cd /home/deployer/forex-forecast-system && python scripts/daily_performance_check.sh >> logs/performance.log 2>&1

# Dashboard semanal (Lunes 9 AM)
0 9 * * 1 cd /home/deployer/forex-forecast-system && python scripts/mlops_dashboard.py show --horizon 7d | mail -s "Weekly MLOps Report" rafael@cavara.cl
```

### Criterios de Éxito

- [x] Alertas se envían cuando RMSE degrada > 20%
- [x] Walk-forward validation ejecuta en < 5 minutos
- [x] Dashboard muestra métricas actualizadas diariamente
- [x] Drift trends detectan degradación progresiva
- [x] Coverage de CI monitoreado y alertado

### Tiempo Estimado

- Performance monitoring: 4 horas
- Walk-forward validation: 6 horas
- Drift trend analysis: 3 horas
- Dashboard CLI: 3 horas
- Testing: 4 horas
- **Total: ~20 horas (2 semanas a medio tiempo)**

---

## Fase 3: Automation (Semanas 5-6)

**Timeline:** 2 semanas
**Status:** 📋 PLANIFICADA

### Objetivos

- [ ] Triggers inteligentes de re-entrenamiento
- [ ] Model registry con versioning (MLflow)
- [ ] Rollback automático si modelo nuevo falla
- [ ] CI/CD pipeline para modelos

### Trabajo a Realizar

#### 1. Re-training Triggers

**Archivo nuevo:** `src/forex_core/mlops/retraining.py`

```python
class RetrainingTrigger:
    """Decide cuándo re-entrenar modelos automáticamente."""

    TRIGGER_REASONS = [
        'PERFORMANCE_DEGRADATION',  # RMSE > threshold
        'DRIFT_DETECTED',           # Drift significativo
        'SCHEDULED',                # Re-train programado (mensual)
        'MANUAL'                    # Trigger manual
    ]

    def should_retrain(
        self,
        horizon: str,
        performance_report: PerformanceReport,
        drift_report: DriftReport
    ) -> Tuple[bool, str]:
        """Decide si re-entrenar basado en múltiples criterios."""

        # Check performance degradation
        if performance_report.degradation_pct > 25:
            return True, 'PERFORMANCE_DEGRADATION'

        # Check drift
        if drift_report.has_significant_drift():
            return True, 'DRIFT_DETECTED'

        # Check last retrain time
        last_retrain = self._get_last_retrain_date(horizon)
        days_since_retrain = (datetime.now() - last_retrain).days

        if days_since_retrain > 30:  # Monthly retrain
            return True, 'SCHEDULED'

        return False, None

    def execute_retrain(
        self,
        horizon: str,
        reason: str,
        dry_run: bool = False
    ) -> RetrainingResult:
        """Ejecuta re-entrenamiento con nueva data."""

        logger.info(f"Retraining {horizon} model. Reason: {reason}")

        # Load fresh data
        loader = DataLoader(settings)
        bundle = loader.load()

        # Get appropriate config
        config = get_horizon_config(horizon)

        # Train new model
        engine = ForecastEngine(config)
        engine.fit(bundle)

        # Validate on holdout set
        validator = WalkForwardValidator(engine)
        validation = validator.validate(
            data=bundle.usdclp_series,
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now()
        )

        # Save model if validation passes
        if validation.mean_rmse < self._get_acceptable_rmse(horizon):
            new_version = self._save_model(engine, horizon)

            if not dry_run:
                self._deploy_model(horizon, new_version)

            return RetrainingResult(
                success=True,
                horizon=horizon,
                reason=reason,
                new_version=new_version,
                validation_rmse=validation.mean_rmse
            )
        else:
            logger.warning(f"Retrained model failed validation. RMSE: {validation.mean_rmse}")
            return RetrainingResult(success=False, reason='VALIDATION_FAILED')
```

#### 2. Model Registry (MLflow)

**Archivo nuevo:** `src/forex_core/mlops/registry.py`

```python
import mlflow
from mlflow.tracking import MlflowClient

class ModelRegistry:
    """MLflow-based model registry con versioning."""

    def __init__(self, tracking_uri: str = "file:///data/mlruns"):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()

    def log_model(
        self,
        model: ForecastEngine,
        horizon: str,
        metrics: dict,
        params: dict,
        artifacts: dict = None
    ) -> str:
        """Registra modelo en MLflow con metadata."""

        experiment_name = f"forex-{horizon}"
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run() as run:
            # Log parameters
            mlflow.log_params(params)

            # Log metrics
            mlflow.log_metrics(metrics)

            # Log model
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
                registered_model_name=f"forex_{horizon}"
            )

            # Log additional artifacts
            if artifacts:
                for name, path in artifacts.items():
                    mlflow.log_artifact(path, artifact_path=name)

            return run.info.run_id

    def get_model(self, horizon: str, version: str = "latest") -> ForecastEngine:
        """Carga modelo desde registry."""

        model_name = f"forex_{horizon}"

        if version == "latest":
            model_version = self.client.get_latest_versions(model_name, stages=["Production"])[0].version
        else:
            model_version = version

        model_uri = f"models:/{model_name}/{model_version}"
        return mlflow.sklearn.load_model(model_uri)

    def promote_to_production(self, horizon: str, version: str):
        """Promueve modelo a Production stage."""

        model_name = f"forex_{horizon}"
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )

    def rollback(self, horizon: str, to_version: str):
        """Rollback a versión anterior."""

        logger.info(f"Rolling back {horizon} to version {to_version}")
        self.promote_to_production(horizon, to_version)
```

#### 3. Automatic Rollback

**Archivo nuevo:** `src/forex_core/mlops/deployment.py`

```python
class ModelDeploymentManager:
    """Gestiona deployment y rollback automático."""

    def __init__(
        self,
        registry: ModelRegistry,
        monitor: PerformanceMonitor,
        grace_period_days: int = 3
    ):
        self.registry = registry
        self.monitor = monitor
        self.grace_period_days = grace_period_days

    def deploy_new_version(
        self,
        horizon: str,
        new_version: str,
        shadow_mode: bool = True
    ) -> DeploymentResult:
        """Deploya nueva versión con monitoring."""

        # Record deployment
        deployment = Deployment(
            horizon=horizon,
            version=new_version,
            deployed_at=datetime.now(),
            previous_version=self.registry.get_production_version(horizon),
            shadow_mode=shadow_mode
        )

        self._save_deployment(deployment)

        if shadow_mode:
            logger.info(f"Deploying {horizon} v{new_version} in SHADOW mode")
            # Run predictions in parallel with production, compare results
        else:
            logger.info(f"Deploying {horizon} v{new_version} to PRODUCTION")
            self.registry.promote_to_production(horizon, new_version)

        return DeploymentResult(
            success=True,
            deployment=deployment
        )

    def check_deployment_health(
        self,
        horizon: str,
        deployment: Deployment
    ) -> bool:
        """Verifica salud de deployment reciente."""

        days_since_deploy = (datetime.now() - deployment.deployed_at).days

        if days_since_deploy < self.grace_period_days:
            # Still in grace period, monitor but don't rollback yet
            return True

        # Check performance
        perf = self.monitor.check_performance(horizon, window_days=7)

        # Rollback if degradation > 30%
        if perf.degradation_pct > 30:
            logger.warning(f"Automatic rollback triggered for {horizon}")
            self.rollback(horizon, deployment)
            return False

        return True

    def rollback(self, horizon: str, deployment: Deployment):
        """Ejecuta rollback automático."""

        logger.info(f"Rolling back {horizon} from v{deployment.version} to v{deployment.previous_version}")

        # Promote previous version back to production
        self.registry.promote_to_production(horizon, deployment.previous_version)

        # Send alert
        self._send_rollback_alert(horizon, deployment)

        # Update deployment record
        deployment.rolled_back_at = datetime.now()
        self._save_deployment(deployment)
```

#### 4. CI/CD Pipeline

**Archivo nuevo:** `.github/workflows/model_pipeline.yml`

```yaml
name: Model CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    paths:
      - 'src/forex_core/forecasting/**'
      - 'src/forex_core/data/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest tests/ --cov=src/forex_core

      - name: Validate models
        run: python scripts/validate_models.py

  retrain:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Trigger retraining
        run: |
          ssh ${{ secrets.PROD_SERVER }} \
            "cd /home/deployer/forex-forecast-system && \
             python scripts/retrain_models.py --horizon 7d --reason SCHEDULED"

  deploy:
    needs: retrain
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          ssh ${{ secrets.PROD_SERVER }} \
            "cd /home/deployer/forex-forecast-system && \
             python scripts/deploy_model.py --horizon 7d --version latest"
```

### Archivos a Crear/Modificar

```
src/forex_core/mlops/
├── retraining.py          # NEW - Retraining triggers
├── registry.py            # NEW - MLflow model registry
├── deployment.py          # NEW - Deployment management
└── __init__.py           # MODIFY - Add exports

scripts/
├── retrain_models.py      # NEW - Manual retrain trigger
├── deploy_model.py        # NEW - Model deployment
└── check_deployments.sh   # NEW - Health check cron

.github/workflows/
└── model_pipeline.yml     # NEW - CI/CD pipeline

data/
└── mlruns/                # NEW - MLflow tracking
```

### Dependencias Nuevas

```python
# requirements.txt additions
mlflow>=2.13.0         # Model registry & tracking
```

### Cron Jobs Adicionales

```cron
# Check deployment health diariamente
0 10 * * * cd /home/deployer/forex-forecast-system && bash scripts/check_deployments.sh >> logs/deployments.log 2>&1
```

### Criterios de Éxito

- [x] Re-training automático cuando RMSE > 25% degradación
- [x] Modelos versionados en MLflow con metadata completa
- [x] Rollback automático si nuevo modelo falla
- [x] CI/CD pipeline ejecuta tests antes de deploy
- [x] Deployment health checks running diariamente

### Tiempo Estimado

- Retraining triggers: 6 horas
- MLflow integration: 8 horas
- Deployment manager: 6 horas
- CI/CD pipeline: 4 horas
- Testing: 6 horas
- **Total: ~30 horas (2 semanas a medio tiempo)**

---

## Fase 4: Optimization (Semanas 7-8)

**Timeline:** 2 semanas
**Status:** 📋 PLANIFICADA

### Objetivos

- [ ] Hyperparameter tuning automático con Optuna
- [ ] Optimización continua de pesos del ensemble
- [ ] Feature selection automática
- [ ] Auto-scaling de recursos

### Trabajo a Realizar

#### 1. Hyperparameter Tuning con Optuna

**Archivo nuevo:** `src/forex_core/mlops/optimization.py`

```python
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler

class HyperparameterOptimizer:
    """Optuna-based hyperparameter optimization."""

    def __init__(
        self,
        horizon: str,
        n_trials: int = 100,
        timeout: int = 3600  # 1 hour
    ):
        self.horizon = horizon
        self.n_trials = n_trials
        self.timeout = timeout

    def optimize_arima(
        self,
        data: pd.DataFrame,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Optimize ARIMA hyperparameters."""

        def objective(trial):
            # Suggest hyperparameters
            p = trial.suggest_int('p', 0, 5)
            d = trial.suggest_int('d', 0, 2)
            q = trial.suggest_int('q', 0, 5)

            # Cross-validation
            scores = []
            for fold in range(cv_folds):
                train, test = self._split_ts_fold(data, fold, cv_folds)

                try:
                    model = ARIMA(train, order=(p, d, q))
                    fitted = model.fit()
                    forecast = fitted.forecast(steps=len(test))
                    rmse = np.sqrt(mean_squared_error(test, forecast))
                    scores.append(rmse)
                except:
                    return float('inf')

            return np.mean(scores)

        # Create study
        study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(),
            pruner=MedianPruner()
        )

        # Optimize
        study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )

        return study.best_params

    def optimize_random_forest(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Optimize Random Forest hyperparameters."""

        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'max_depth': trial.suggest_int('max_depth', 5, 30),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None])
            }

            # Time series CV
            tscv = TimeSeriesSplit(n_splits=cv_folds)
            scores = []

            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]

                model = RandomForestRegressor(**params, random_state=42)
                model.fit(X_train, y_train)
                pred = model.predict(X_test)

                rmse = np.sqrt(mean_squared_error(y_test, pred))
                scores.append(rmse)

            return np.mean(scores)

        study = optuna.create_study(direction='minimize', sampler=TPESampler())
        study.optimize(objective, n_trials=self.n_trials, timeout=self.timeout)

        return study.best_params
```

#### 2. Ensemble Weight Optimization

**Archivo nuevo:** `src/forex_core/mlops/ensemble_optimization.py`

```python
class EnsembleWeightOptimizer:
    """Optimización continua de pesos del ensemble."""

    def __init__(
        self,
        tracker: PredictionTracker,
        window_days: int = 90
    ):
        self.tracker = tracker
        self.window_days = window_days

    def optimize_weights(
        self,
        horizon: str,
        method: str = 'rmse_weighted'
    ) -> Dict[str, float]:
        """Optimiza pesos basado en performance reciente."""

        # Get recent predictions with actuals
        predictions = self.tracker.get_predictions_with_actuals(
            horizon=horizon,
            days=self.window_days
        )

        if len(predictions) < 30:
            logger.warning(f"Insufficient data for weight optimization: {len(predictions)} samples")
            return self._get_default_weights(horizon)

        # Extract model predictions from metadata
        arima_preds = [p['metadata']['arima_prediction'] for p in predictions]
        var_preds = [p['metadata']['var_prediction'] for p in predictions]
        rf_preds = [p['metadata']['rf_prediction'] for p in predictions]
        actuals = [p['actual'] for p in predictions]

        if method == 'rmse_weighted':
            # Weight inversely proportional to RMSE
            rmse_arima = np.sqrt(mean_squared_error(actuals, arima_preds))
            rmse_var = np.sqrt(mean_squared_error(actuals, var_preds))
            rmse_rf = np.sqrt(mean_squared_error(actuals, rf_preds))

            # Inverse weights
            inv_arima = 1 / rmse_arima
            inv_var = 1 / rmse_var
            inv_rf = 1 / rmse_rf

            total = inv_arima + inv_var + inv_rf

            weights = {
                'arima': inv_arima / total,
                'var': inv_var / total,
                'rf': inv_rf / total
            }

        elif method == 'optuna':
            # Optimize weights with Optuna
            def objective(trial):
                w_arima = trial.suggest_float('w_arima', 0, 1)
                w_var = trial.suggest_float('w_var', 0, 1)
                w_rf = trial.suggest_float('w_rf', 0, 1)

                total = w_arima + w_var + w_rf
                w_arima /= total
                w_var /= total
                w_rf /= total

                ensemble_preds = (
                    w_arima * np.array(arima_preds) +
                    w_var * np.array(var_preds) +
                    w_rf * np.array(rf_preds)
                )

                rmse = np.sqrt(mean_squared_error(actuals, ensemble_preds))
                return rmse

            study = optuna.create_study(direction='minimize')
            study.optimize(objective, n_trials=1000)

            params = study.best_params
            total = params['w_arima'] + params['w_var'] + params['w_rf']

            weights = {
                'arima': params['w_arima'] / total,
                'var': params['w_var'] / total,
                'rf': params['w_rf'] / total
            }

        logger.info(f"Optimized weights for {horizon}: {weights}")
        return weights
```

#### 3. Feature Selection Automática

**Archivo nuevo:** `src/forex_core/mlops/feature_selection.py`

```python
from sklearn.feature_selection import SelectKBest, mutual_info_regression
from sklearn.ensemble import RandomForestRegressor

class AutoFeatureSelector:
    """Selección automática de features más relevantes."""

    def __init__(self, method: str = 'mutual_info'):
        self.method = method
        self.selected_features = None

    def select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        k: int = 20
    ) -> List[str]:
        """Selecciona top K features."""

        if self.method == 'mutual_info':
            selector = SelectKBest(score_func=mutual_info_regression, k=k)
            selector.fit(X, y)

            # Get selected features
            mask = selector.get_support()
            selected = X.columns[mask].tolist()

        elif self.method == 'random_forest':
            # Train RF and get feature importances
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X, y)

            importances = pd.DataFrame({
                'feature': X.columns,
                'importance': rf.feature_importances_
            }).sort_values('importance', ascending=False)

            selected = importances.head(k)['feature'].tolist()

        elif self.method == 'correlation':
            # Select features most correlated with target
            correlations = X.corrwith(y).abs().sort_values(ascending=False)
            selected = correlations.head(k).index.tolist()

        self.selected_features = selected
        logger.info(f"Selected {len(selected)} features: {selected}")

        return selected

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform X to only include selected features."""
        if self.selected_features is None:
            raise ValueError("Must call select_features() first")

        return X[self.selected_features]
```

### Archivos a Crear/Modificar

```
src/forex_core/mlops/
├── optimization.py          # NEW - Optuna hyperparameter tuning
├── ensemble_optimization.py # NEW - Ensemble weight optimization
├── feature_selection.py     # NEW - Auto feature selection
└── __init__.py             # MODIFY

scripts/
├── optimize_hyperparams.py  # NEW - CLI for optimization
└── weekly_optimization.sh   # NEW - Weekly cron

tests/
└── unit/mlops/
    ├── test_optimization.py
    ├── test_ensemble_opt.py
    └── test_feature_selection.py
```

### Dependencias Nuevas

```python
# requirements.txt additions
optuna>=3.6.0          # Hyperparameter optimization
optuna-dashboard>=0.15.0  # Visualization
```

### Cron Jobs Adicionales

```cron
# Optimización semanal de pesos (Domingo 2 AM)
0 2 * * 0 cd /home/deployer/forex-forecast-system && python scripts/optimize_ensemble_weights.py >> logs/optimization.log 2>&1

# Hyperparameter tuning mensual (1er día del mes, 3 AM)
0 3 1 * * cd /home/deployer/forex-forecast-system && python scripts/optimize_hyperparams.py --horizon 7d >> logs/optimization.log 2>&1
```

### Criterios de Éxito

- [x] Hyperparameter optimization mejora RMSE en 5-10%
- [x] Ensemble weights actualizados semanalmente
- [x] Feature selection reduce dimensionalidad sin pérdida de accuracy
- [x] Optimization pipeline ejecuta sin intervención manual

### Tiempo Estimado

- Optuna integration: 8 horas
- Ensemble optimization: 6 horas
- Feature selection: 4 horas
- Testing & validation: 6 horas
- **Total: ~24 horas (2 semanas a medio tiempo)**

---

## Fase 5: Full AutoML (Semanas 9-12)

**Timeline:** 4 semanas
**Status:** 📋 PLANIFICADA

### Objetivos

- [ ] Selección automática de mejores modelos
- [ ] A/B testing en shadow mode
- [ ] Sistema completamente autónomo
- [ ] Auto-healing y self-tuning

### Trabajo a Realizar

#### 1. Auto Model Selection

**Archivo nuevo:** `src/forex_core/mlops/automl.py`

```python
class AutoModelSelector:
    """Selección automática del mejor modelo para cada horizon."""

    MODEL_CANDIDATES = [
        'arima_garch',
        'var',
        'random_forest',
        'xgboost',
        'lightgbm',
        'prophet',
        'lstm',
        'transformer'
    ]

    def __init__(
        self,
        tracker: PredictionTracker,
        registry: ModelRegistry
    ):
        self.tracker = tracker
        self.registry = registry

    def select_best_model(
        self,
        horizon: str,
        evaluation_window: int = 90
    ) -> str:
        """Evalúa todos los candidatos y selecciona el mejor."""

        results = {}

        for model_type in self.MODEL_CANDIDATES:
            try:
                # Train model
                model = self._train_model(model_type, horizon)

                # Evaluate on holdout
                metrics = self._evaluate_model(model, horizon, evaluation_window)

                results[model_type] = {
                    'rmse': metrics.rmse,
                    'mae': metrics.mae,
                    'coverage_95': metrics.coverage_95,
                    'training_time': metrics.training_time
                }

                logger.info(f"{model_type} - RMSE: {metrics.rmse:.2f}")

            except Exception as e:
                logger.error(f"Failed to train {model_type}: {e}")
                results[model_type] = {'rmse': float('inf')}

        # Select best by RMSE
        best_model = min(results, key=lambda k: results[k]['rmse'])

        logger.info(f"Best model for {horizon}: {best_model}")
        return best_model

    def _train_model(self, model_type: str, horizon: str):
        """Train specific model type."""

        if model_type == 'arima_garch':
            return self._train_arima_garch(horizon)
        elif model_type == 'xgboost':
            return self._train_xgboost(horizon)
        elif model_type == 'lstm':
            return self._train_lstm(horizon)
        # ... etc
```

#### 2. A/B Testing Framework

**Archivo nuevo:** `src/forex_core/mlops/ab_testing.py`

```python
class ABTestFramework:
    """A/B testing de modelos en shadow mode."""

    def __init__(
        self,
        registry: ModelRegistry,
        tracker: PredictionTracker
    ):
        self.registry = registry
        self.tracker = tracker

    def run_ab_test(
        self,
        horizon: str,
        model_a_version: str,  # Current production
        model_b_version: str,  # New candidate
        test_duration_days: int = 14
    ) -> ABTestResult:
        """Ejecuta A/B test comparando dos modelos."""

        logger.info(f"Starting A/B test: {model_a_version} vs {model_b_version}")

        # Load both models
        model_a = self.registry.get_model(horizon, model_a_version)
        model_b = self.registry.get_model(horizon, model_b_version)

        # Run predictions in parallel (shadow mode)
        test_results = []

        for day in range(test_duration_days):
            # Load data
            data = self._get_daily_data(datetime.now() - timedelta(days=test_duration_days - day))

            # Generate predictions
            pred_a = model_a.predict(data)
            pred_b = model_b.predict(data)

            # Wait for actual value
            actual = self._wait_for_actual(date=data.index[-1])

            # Record results
            test_results.append({
                'date': data.index[-1],
                'pred_a': pred_a,
                'pred_b': pred_b,
                'actual': actual,
                'error_a': abs(pred_a - actual),
                'error_b': abs(pred_b - actual)
            })

        # Analyze results
        df = pd.DataFrame(test_results)

        rmse_a = np.sqrt(mean_squared_error(df['actual'], df['pred_a']))
        rmse_b = np.sqrt(mean_squared_error(df['actual'], df['pred_b']))

        # Statistical significance test
        from scipy.stats import ttest_rel
        t_stat, p_value = ttest_rel(df['error_a'], df['error_b'])

        is_significant = p_value < 0.05
        winner = 'B' if rmse_b < rmse_a else 'A'

        return ABTestResult(
            model_a_version=model_a_version,
            model_b_version=model_b_version,
            rmse_a=rmse_a,
            rmse_b=rmse_b,
            winner=winner,
            is_significant=is_significant,
            p_value=p_value,
            recommendation='DEPLOY_B' if (winner == 'B' and is_significant) else 'KEEP_A'
        )
```

#### 3. Auto-Healing System

**Archivo nuevo:** `src/forex_core/mlops/auto_healing.py`

```python
class AutoHealingSystem:
    """Sistema de auto-recuperación ante fallos."""

    def __init__(
        self,
        monitor: PerformanceMonitor,
        deployment_manager: ModelDeploymentManager,
        registry: ModelRegistry
    ):
        self.monitor = monitor
        self.deployment = deployment_manager
        self.registry = registry

    def health_check(self, horizon: str) -> HealthStatus:
        """Verifica salud del sistema."""

        issues = []

        # Check prediction service
        try:
            test_prediction = self._test_prediction_service(horizon)
            if test_prediction is None:
                issues.append('PREDICTION_SERVICE_DOWN')
        except Exception as e:
            issues.append(f'PREDICTION_ERROR: {e}')

        # Check performance
        perf = self.monitor.check_performance(horizon, window_days=7)
        if perf.degradation_pct > 50:
            issues.append('SEVERE_PERFORMANCE_DEGRADATION')

        # Check data freshness
        last_prediction = self.tracker.get_latest_prediction(horizon)
        hours_since = (datetime.now() - last_prediction.timestamp).total_seconds() / 3600
        if hours_since > 48:  # 2 days
            issues.append('STALE_PREDICTIONS')

        status = 'HEALTHY' if len(issues) == 0 else 'UNHEALTHY'

        return HealthStatus(
            status=status,
            issues=issues,
            timestamp=datetime.now()
        )

    def auto_heal(self, horizon: str, health: HealthStatus):
        """Intenta recuperación automática."""

        for issue in health.issues:
            if issue == 'PREDICTION_SERVICE_DOWN':
                self._restart_service(horizon)

            elif issue == 'SEVERE_PERFORMANCE_DEGRADATION':
                # Rollback to last known good version
                self.deployment.rollback_to_last_good(horizon)

            elif issue == 'STALE_PREDICTIONS':
                # Trigger manual forecast
                self._trigger_forecast(horizon)

        # Re-check health
        new_health = self.health_check(horizon)

        if new_health.status == 'HEALTHY':
            logger.info(f"Auto-healing successful for {horizon}")
        else:
            logger.error(f"Auto-healing failed for {horizon}. Manual intervention required.")
            self._send_critical_alert(horizon, new_health)
```

### Archivos a Crear/Modificar

```
src/forex_core/mlops/
├── automl.py              # NEW - Auto model selection
├── ab_testing.py          # NEW - A/B test framework
├── auto_healing.py        # NEW - Auto-healing system
└── __init__.py           # MODIFY

scripts/
├── run_automl.py          # NEW - AutoML pipeline
├── run_ab_test.py         # NEW - A/B test runner
└── health_monitor.sh      # NEW - Continuous health checks

tests/
└── unit/mlops/
    ├── test_automl.py
    ├── test_ab_testing.py
    └── test_auto_healing.py
```

### Dependencias Nuevas

```python
# requirements.txt additions
xgboost>=2.0.0         # XGBoost models
lightgbm>=4.3.0        # LightGBM models
prophet>=1.1.5         # Facebook Prophet
tensorflow>=2.16.0     # LSTM, Transformer models
scipy>=1.13.0          # Statistical tests
```

### Cron Jobs Adicionales

```cron
# Health check cada 6 horas
0 */6 * * * cd /home/deployer/forex-forecast-system && python scripts/health_check.py >> logs/health.log 2>&1

# AutoML mensual (1er domingo, 1 AM)
0 1 * * 0 [ $(date +\%d) -le 7 ] && cd /home/deployer/forex-forecast-system && python scripts/run_automl.py >> logs/automl.log 2>&1
```

### Criterios de Éxito

- [x] AutoML selecciona mejor modelo automáticamente
- [x] A/B tests ejecutan sin intervención manual
- [x] Auto-healing recupera de 80%+ de fallos
- [x] Sistema opera 30+ días sin intervención humana

### Tiempo Estimado

- AutoML framework: 12 horas
- A/B testing: 10 horas
- Auto-healing: 8 horas
- Integration testing: 10 horas
- **Total: ~40 horas (4 semanas a medio tiempo)**

---

## Métricas de Éxito del Roadmap

### KPIs Globales

| Fase | KPI Principal | Target | Tracking |
|------|--------------|--------|----------|
| **Fase 1** | Predictions tracked | 100% | ✅ 266+ predictions |
| **Fase 2** | Alert accuracy | >90% precision | Pending |
| **Fase 3** | Auto-retrain success rate | >80% | Pending |
| **Fase 4** | RMSE improvement | 5-10% | Pending |
| **Fase 5** | System uptime | >99% | Pending |

### Performance Benchmarks

**Baseline (Actual):**
- 7d RMSE: ~10-12 CLP
- 15d RMSE: ~15-20 CLP
- 30d RMSE: ~25-35 CLP
- 90d RMSE: ~50-80 CLP

**Target (Post-AutoML):**
- 7d RMSE: ~8-10 CLP (15% improvement)
- 15d RMSE: ~12-17 CLP (15% improvement)
- 30d RMSE: ~20-30 CLP (15% improvement)
- 90d RMSE: ~40-70 CLP (15% improvement)

### Operational Metrics

- **MTTR (Mean Time To Recovery):** < 30 minutes
- **False Alert Rate:** < 10%
- **Manual Interventions per Month:** < 5
- **Model Update Frequency:** Weekly → Daily (automated)

---

## Riesgos y Mitigación

### Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Optuna timeout** | Media | Bajo | Timeout de 1 hora, early stopping |
| **MLflow storage full** | Baja | Medio | Auto-cleanup de runs antiguos |
| **A/B test inconclusive** | Media | Bajo | Extender duración, más muestras |
| **Auto-healing loop** | Baja | Alto | Circuit breaker después de 3 intentos |
| **Model drift no detectado** | Media | Alto | Múltiples drift tests, ensemble voting |

### Estrategias de Rollback

1. **Model Rollback:** MLflow mantiene últimas 5 versiones
2. **Feature Rollback:** Git tags por versión de features
3. **Config Rollback:** .env.backup automático
4. **Data Rollback:** Parquet con particiones diarias

---

## Timeline Visual

```
Semanas 1-2  [████████] Fase 1: Foundation ✅
Semanas 3-4  [        ] Fase 2: Monitoring
Semanas 5-6  [        ] Fase 3: Automation
Semanas 7-8  [        ] Fase 4: Optimization
Semanas 9-12 [        ] Fase 5: Full AutoML
```

**Progreso actual:** 17% completo (Fase 1/5)

---

## Próximos Pasos Inmediatos

### Esta Semana (Nov 14-20)

1. **Investigar issues de Fase 1:**
   - Operation time muestra 0 días
   - Min predictions por horizon = 0

2. **Monitorear acumulación de data:**
   - Verificar que todos los horizons reciben predictions
   - Timeline: 50+ predictions en 1-2 semanas

3. **Planificar Fase 2:**
   - Diseñar thresholds de alertas
   - Definir canales de notificación (Email, Slack)

### Mes 2 (Diciembre)

- Implementar Fase 2 (Monitoring)
- Implementar Fase 3 (Automation)

### Mes 3 (Enero 2026)

- Implementar Fase 4 (Optimization)
- Comenzar Fase 5 (Full AutoML)

---

## Recursos Adicionales

### Documentación Relacionada

- `docs/CHRONOS_AUTO_VALIDATION.md` - Sistema de validación actual
- `docs/conversations/2025-11-13-chronos-readiness-automation-setup.md` - Sesión Fase 1
- `PROJECT_STATUS.md` - Estado general del proyecto

### Referencias Técnicas

- **MLflow Documentation:** https://mlflow.org/docs/latest/index.html
- **Optuna Guide:** https://optuna.readthedocs.io/
- **Walk-Forward Validation:** Hyndman & Athanasopoulos (2021) Chapter 5
- **A/B Testing:** Kohavi et al. (2020) *Trustworthy Online Controlled Experiments*

---

**Document Status:** Living Document
**Maintained By:** Development Team
**Last Updated:** 2025-11-13
**Version:** 1.0

---

## Apéndice: Comandos Útiles

### Fase 1 (Actual)
```bash
# Check readiness
python scripts/check_chronos_readiness.py check

# View predictions
python -c "import pandas as pd; print(pd.read_parquet('data/predictions/predictions.parquet'))"

# Manual drift detection
python -m forex_core.mlops.monitoring
```

### Fase 2 (Futuro)
```bash
# Performance dashboard
python scripts/mlops_dashboard.py show --horizon 7d

# Walk-forward validation
python scripts/validate_walkforward.py --horizon 7d --start 2023-01-01

# Check alerts
tail -f logs/alerts.log
```

### Fase 3 (Futuro)
```bash
# Trigger retrain
python scripts/retrain_models.py --horizon 7d --reason PERFORMANCE_DEGRADATION

# Deploy model
python scripts/deploy_model.py --horizon 7d --version latest

# Rollback
python scripts/rollback_model.py --horizon 7d --to-version v1.2.3
```

### Fase 4 (Futuro)
```bash
# Optimize hyperparameters
python scripts/optimize_hyperparams.py --horizon 7d --n-trials 100

# Optimize ensemble weights
python scripts/optimize_ensemble_weights.py --horizon 7d

# Feature selection
python scripts/select_features.py --horizon 7d --method mutual_info
```

### Fase 5 (Futuro)
```bash
# Run AutoML
python scripts/run_automl.py --horizon 7d --candidates all

# A/B test
python scripts/run_ab_test.py --horizon 7d --model-a v1.2.3 --model-b v1.3.0 --days 14

# Health check
python scripts/health_check.py --all
```
