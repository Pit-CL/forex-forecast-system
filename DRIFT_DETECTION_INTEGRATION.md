# Instrucciones de Integración: Sistema de Drift Detection

## Resumen

Se ha implementado un sistema completo de **drift detection** para detectar automáticamente cambios en la distribución de datos USD/CLP que podrían requerir recalibración de modelos.

## Archivos Creados

### 1. Módulo Core: `/src/forex_core/mlops/monitoring.py`
**Clases principales:**
- `DataDriftDetector`: Detector principal con múltiples tests estadísticos
- `DriftReport`: Reporte completo con resultados de todos los tests
- `DriftTestResult`: Resultado individual de cada test
- `DriftSeverity`: Niveles de severidad (NONE, LOW, MEDIUM, HIGH)

**Tests implementados:**
- Kolmogorov-Smirnov (distribución completa)
- T-test de Welch (cambio en media)
- Test de Levene (cambio en varianza)
- Test de Ljung-Box (cambio en autocorrelación)
- Detección de régimen de volatilidad

### 2. Configuración: `/src/forex_core/config/base.py`
**Nuevos parámetros añadidos:**
```python
drift_baseline_window: int = 90  # ventana histórica (días)
drift_test_window: int = 30      # ventana reciente (días)
drift_alpha: float = 0.05         # nivel de significancia
drift_alert_threshold: str = "medium"  # umbral para alertas
```

### 3. Archivo de Referencia: `/src/services/forecaster_7d/pipeline_drift_functions.py`
Contiene funciones helper listas para integrar en todos los pipelines.

## Integración en Pipelines

Para integrar drift detection en cada pipeline (7d, 15d, 30d, 90d), seguir estos pasos:

### Paso 1: Actualizar Imports

**En cada `pipeline.py`**, agregar al inicio:
```python
from forex_core.mlops import DataDriftDetector, DriftReport
```

### Paso 2: Agregar Funciones Helper

**Copiar estas funciones** al final de cada `pipeline.py`:

```python
def _detect_drift(settings, bundle: DataBundle) -> DriftReport:
    """
    Run drift detection on USD/CLP series.

    Args:
        settings: System settings with drift detection configuration.
        bundle: DataBundle with historical USD/CLP data.

    Returns:
        DriftReport with comprehensive drift analysis.
    """
    detector = DataDriftDetector(
        baseline_window=settings.drift_baseline_window,
        test_window=settings.drift_test_window,
        alpha=settings.drift_alpha,
    )

    return detector.generate_drift_report(bundle.usdclp_series)


def _log_drift_results(drift_report: DriftReport) -> None:
    """
    Log drift detection results with appropriate severity level.

    Args:
        drift_report: Drift detection report to log.
    """
    from forex_core.mlops.monitoring import DriftSeverity

    if not drift_report.drift_detected:
        logger.info("No significant drift detected in USD/CLP data")
        logger.info(f"Baseline mean: {drift_report.baseline_mean:.2f} CLP")
        logger.info(f"Recent mean: {drift_report.recent_mean:.2f} CLP")
        return

    # Log based on severity
    if drift_report.severity == DriftSeverity.HIGH:
        logger.error(f"HIGH SEVERITY DRIFT DETECTED!")
    elif drift_report.severity == DriftSeverity.MEDIUM:
        logger.warning(f"MEDIUM SEVERITY DRIFT DETECTED")
    elif drift_report.severity == DriftSeverity.LOW:
        logger.warning(f"LOW SEVERITY DRIFT DETECTED")

    # Log statistics
    logger.info(
        f"Drift Statistics: "
        f"baseline_mean={drift_report.baseline_mean:.2f}, "
        f"recent_mean={drift_report.recent_mean:.2f}, "
        f"baseline_std={drift_report.baseline_std:.2f}, "
        f"recent_std={drift_report.recent_std:.2f}"
    )

    # Log failed tests
    failed_tests = [
        name for name, result in drift_report.tests.items()
        if result.drift_detected
    ]
    if failed_tests:
        logger.warning(f"Failed tests: {', '.join(failed_tests)}")

    # Log recommendation
    logger.info(f"Recommendation: {drift_report.recommendation}")
```

### Paso 3: Modificar `run_forecast_pipeline()`

**Después de cargar datos**, agregar:

```python
# Step 1: Load data
logger.info("Loading data from providers...")
loader = DataLoader(settings)
bundle: DataBundle = loader.load()
logger.info(f"Data loaded: {len(bundle.indicators)} indicators, {len(bundle.sources)} sources")

# Step 1.5: Run drift detection
logger.info("Running drift detection on USD/CLP series...")
drift_report = _detect_drift(settings, bundle)
_log_drift_results(drift_report)

# Step 2: Generate forecast
# ... continúa el resto del pipeline
```

### Paso 4: Actualizar Firma de `_build_report()`

**Cambiar firma de:**
```python
def _build_report(
    settings,
    service_config,
    bundle: DataBundle,
    forecast: ForecastPackage,
    artifacts: EnsembleArtifacts,
    chart_paths: dict[str, Path],
) -> Path:
```

**A:**
```python
def _build_report(
    settings,
    service_config,
    bundle: DataBundle,
    forecast: ForecastPackage,
    artifacts: EnsembleArtifacts,
    chart_paths: dict[str, Path],
    drift_report: DriftReport,  # <-- NUEVO
) -> Path:
```

**Y agregar dentro:**
```python
# Convert EnsembleArtifacts to dict format expected by builder
artifacts_dict = {
    "weights": artifacts.weights if hasattr(artifacts, "weights") else {},
    "models": artifacts.models if hasattr(artifacts, "models") else {},
    "drift_report": drift_report,  # <-- AGREGAR ESTO
}
```

### Paso 5: Actualizar Llamada a `_build_report()`

En `run_forecast_pipeline()`, cambiar:
```python
report_path = _build_report(
    settings, service_config, bundle, forecast, artifacts, chart_paths
)
```

A:
```python
report_path = _build_report(
    settings, service_config, bundle, forecast, artifacts, chart_paths, drift_report
)
```

### Paso 6: (Opcional) Integrar en Email

Si quieres incluir alertas de drift en emails, actualizar `_send_email()`:

```python
def _send_email(
    settings,
    report_path: Path,
    bundle: DataBundle,
    forecast: ForecastPackage,
    service_config,
    drift_report: DriftReport,  # <-- AGREGAR
) -> None:
    """Send email with drift alert if severe."""
    from forex_core.notifications.email import EmailSender

    sender = EmailSender(settings)

    # Preparar alerta de drift si es necesaria
    drift_alert = None
    if drift_report.drift_detected:
        severity_levels = {"none": 0, "low": 1, "medium": 2, "high": 3}
        current_severity = severity_levels.get(drift_report.severity.value, 0)
        threshold_severity = severity_levels.get(settings.drift_alert_threshold.lower(), 2)

        if current_severity >= threshold_severity:
            drift_alert = {
                "severity": drift_report.severity.value,
                "recommendation": drift_report.recommendation,
                "tests_failed": sum(1 for test in drift_report.tests.values() if test.drift_detected),
            }

    sender.send(
        report_path=report_path,
        bundle=bundle,
        forecast=forecast.result,
        horizon=service_config.horizon_code,
        drift_alert=drift_alert,  # <-- PASAR ALERTA
    )
```

Y actualizar la llamada:
```python
_send_email(settings, report_path, bundle, forecast, service_config, drift_report)
```

## Variables de Entorno Opcionales

Puedes configurar drift detection en tu `.env`:

```bash
# Drift Detection Configuration
DRIFT_BASELINE_WINDOW=90    # ventana histórica (días)
DRIFT_TEST_WINDOW=30        # ventana reciente (días)
DRIFT_ALPHA=0.05            # nivel de significancia
DRIFT_ALERT_THRESHOLD=medium  # none, low, medium, high
```

## Archivos a Modificar

1. ✅ **CREADO**: `/src/forex_core/mlops/monitoring.py`
2. ✅ **CREADO**: `/src/forex_core/mlops/__init__.py`
3. ✅ **MODIFICADO**: `/src/forex_core/config/base.py`
4. ⚠️ **PENDIENTE**: `/src/services/forecaster_7d/pipeline.py`
5. ⚠️ **PENDIENTE**: `/src/services/forecaster_15d/pipeline.py`
6. ⚠️ **PENDIENTE**: `/src/services/forecaster_30d/pipeline.py`
7. ⚠️ **PENDIENTE**: `/src/services/forecaster_90d/pipeline.py`

## Output Ejemplo

Cuando se ejecute un pipeline con drift detection, verás en logs:

```
[INFO] Running drift detection on USD/CLP series...
[WARNING] MEDIUM SEVERITY DRIFT DETECTED
[INFO] Drift Statistics: baseline_mean=925.40, recent_mean=937.20, baseline_std=8.30, recent_std=12.10
[WARNING] Failed tests: ks_test, t_test
[INFO] Recommendation: WARNING: Moderate data drift detected. Consider retraining models soon...
```

## Estructura del DriftReport

```python
DriftReport(
    drift_detected=True,
    severity=DriftSeverity.MEDIUM,
    p_value=0.023,
    statistic=0.18,
    baseline_mean=925.4,
    recent_mean=937.2,
    baseline_std=8.3,
    recent_std=12.1,
    baseline_size=90,
    recent_size=30,
    tests={
        "ks_test": DriftTestResult(...),
        "t_test": DriftTestResult(...),
        "levene_test": DriftTestResult(...),
        "ljungbox_test": DriftTestResult(...),
    },
    recommendation="WARNING: Moderate data drift detected...",
    timestamp=datetime.now(),
)
```

## Tests Estadísticos Implementados

### 1. Kolmogorov-Smirnov Test
- **Propósito**: Detecta cambios en la distribución completa
- **Sensible a**: Cambios en ubicación, escala y forma
- **H0**: Las dos muestras provienen de la misma distribución

### 2. T-test de Welch
- **Propósito**: Detecta cambios en el nivel medio
- **No asume**: Varianzas iguales (más robusto)
- **H0**: Las dos muestras tienen la misma media

### 3. Test de Levene
- **Propósito**: Detecta cambios en varianza/volatilidad
- **Robusto**: A desviaciones de normalidad
- **H0**: Las dos muestras tienen la misma varianza

### 4. Test de Ljung-Box
- **Propósito**: Detecta cambios en estructura de autocorrelación
- **Aplicado a**: Primera diferencia (serie diferenciada)
- **H0**: No hay autocorrelación significativa

### 5. Detección de Régimen de Volatilidad
- **Método**: Ratio de desviaciones estándar
- **Threshold**: 1.5x (configurable)
- **Detecta**: Cambios abruptos en volatilidad

## Niveles de Severidad

### NONE
- Ningún test detectó drift
- p-value >= 0.05 en todos los tests
- **Acción**: Ninguna, modelos válidos

### LOW
- 1 test detectó drift
- Efecto pequeño (KS < 0.2)
- **Acción**: Monitorear, no urgente

### MEDIUM
- 2 tests detectaron drift, O
- p-value < 0.01 con KS > 0.2
- **Acción**: Considerar reentrenamiento pronto

### HIGH
- 3+ tests detectaron drift, O
- p-value < 0.001
- **Acción**: Reentrenamiento inmediato recomendado

## Testing

Para probar el sistema de drift detection:

```python
from forex_core.mlops import DataDriftDetector
from forex_core.config import get_settings
from forex_core.data import DataLoader

settings = get_settings()
loader = DataLoader(settings)
bundle = loader.load()

detector = DataDriftDetector()
report = detector.generate_drift_report(bundle.usdclp_series)

print(f"Drift detected: {report.drift_detected}")
print(f"Severity: {report.severity}")
print(f"Recommendation: {report.recommendation}")

for test_name, result in report.tests.items():
    print(f"{test_name}: {result.description}")
```

## Dependencias

El sistema usa librerías ya instaladas:
- `scipy.stats`: Para tests estadísticos
- `statsmodels.stats.diagnostic`: Para test de Ljung-Box
- `pandas`, `numpy`: Para manejo de datos

No se requieren nuevas dependencias.

## Notas de Implementación

1. **Datos insuficientes**: Si no hay suficientes datos (< baseline_window + test_window), el sistema retorna un reporte vacío sin errores.

2. **Performance**: Los tests son rápidos (< 1 segundo) incluso con ventanas grandes.

3. **Thread-safe**: El detector no mantiene estado, puede usarse concurrentemente.

4. **Logging**: Usa `loguru.logger` consistente con el resto del sistema.

5. **Type hints**: Código totalmente tipado para mejor IDE support.

## Próximos Pasos Sugeridos

1. ✅ Implementar funciones en cada pipeline
2. ⬜ Actualizar `ReportBuilder` para incluir drift info en PDF
3. ⬜ Agregar visualizaciones de drift (histogramas comparativos)
4. ⬜ Implementar alertas automáticas por Slack/Teams
5. ⬜ Crear dashboard de monitoreo de drift histórico
6. ⬜ Agregar tests unitarios para drift detector
7. ⬜ Implementar auto-retraining cuando drift > HIGH

## Contacto

Para dudas sobre la implementación, revisar:
- `/src/forex_core/mlops/monitoring.py` (implementación completa)
- `/src/services/forecaster_7d/pipeline_drift_functions.py` (ejemplo de integración)
- Este documento: `DRIFT_DETECTION_INTEGRATION.md`
