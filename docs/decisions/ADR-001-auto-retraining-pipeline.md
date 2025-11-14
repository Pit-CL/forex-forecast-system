# ADR-001: Auto-Retraining Pipeline para Modelos Chronos

**Fecha:** 2025-01-13
**Status:** Proposed
**Deciders:** Tech Lead Agent, System Architect
**Sistema:** USD/CLP Forex Forecasting - Chronos Models

---

## Contexto

### Problema a Resolver

El sistema de forecasting USD/CLP utiliza modelos Chronos (foundation models de Hugging Face) que **no requieren retraining tradicional** (son zero-shot). Sin embargo, el sistema actual tiene gaps críticos:

1. **Performance degradation no detectada:** Los modelos pueden volverse menos precisos sin que nadie lo note
2. **Drift detection no automatizado:** Ya existe `DataDriftDetector` y `PerformanceMonitor`, pero no hay acción automática
3. **Validación manual:** El proceso de validación de modelos es ad-hoc
4. **Sin rollback strategy:** No hay forma de volver a configuraciones previas si algo falla

### Aclaración Importante: Chronos NO se Reentrena

**Chronos es un foundation model pretrained**. No hacemos fine-tuning ni retraining del modelo en sí. Lo que sí hacemos:

- **Recalibrar hiperparámetros** (context_length, num_samples, temperature)
- **Ajustar ventanas de contexto** según régimen de mercado
- **Cambiar estrategias de ensemble** si múltiples horizontes
- **Actualizar data preprocessing** (normalización, feature engineering)

Por tanto, este ADR redefine "retraining" como **"recalibración y optimización del pipeline"**.

---

## Fuerzas en Juego

### Necesidades:
- Detectar automáticamente cuando el modelo degrada en performance
- Responder automáticamente a data drift significativo
- Mantener calidad de forecasts sin intervención manual
- Minimizar downtime y riesgo de forecasts erróneos

### Restricciones:
- **VPS Vultr:** Recursos limitados (CPU, RAM)
- **No GPU:** Inferencia en CPU solamente
- **Chronos no se reentrena:** Solo ajustamos hiperparámetros
- **1 desarrollador:** Debe ser mantenible
- **Producción 24/7:** No puede romper forecasting activo

### Trade-offs:
- **Automatización vs Control:** Más automatización = menos control manual
- **Complejidad vs Simplicidad:** Pipeline sofisticado vs script simple
- **Recursos vs Features:** VPS limitado vs features avanzadas
- **Velocidad vs Calidad:** Reacción rápida vs validación exhaustiva

### Timeline: Mediano plazo (3-4 semanas)
### Budget: $0 (solo opensource/free)

---

## Opciones Consideradas

### Opción 1: Container Dedicado "Model Optimizer"

**Descripción:**
Crear un servicio Docker independiente `model-optimizer` que:
- Corre como cron job semanal (o trigger-based)
- Monitorea performance y drift usando módulos existentes
- Ejecuta optimization pipeline cuando detecta degradación
- Genera nuevos configs optimizados
- Valida contra baseline
- Actualiza configs en producción si validación pasa

**Arquitectura:**
```
┌─────────────────────────────────────────────────────────────┐
│                     VPS Vultr (Production)                   │
├─────────────────────────────────────────────────────────────┤
│  Forecaster Containers (4)         Model Optimizer          │
│  ┌─────────────┐                   ┌──────────────┐         │
│  │ forecaster  │◄──────────────────┤ Optimization │         │
│  │   -7d       │ Updated configs   │   Pipeline   │         │
│  │ (Chronos)   │                   │              │         │
│  └─────────────┘                   │ • Monitor    │         │
│                                     │ • Calibrate  │         │
│  ┌─────────────┐                   │ • Validate   │         │
│  │ forecaster  │◄──────────────────┤ • Deploy     │         │
│  │   -15d      │                   └──────────────┘         │
│  └─────────────┘                          ▲                 │
│                                            │                 │
│  ┌─────────────┐                   ┌──────┴───────┐         │
│  │ forecaster  │                   │ Drift &      │         │
│  │   -30d      │                   │ Performance  │         │
│  └─────────────┘                   │ Monitors     │         │
│                                     └──────────────┘         │
│  ┌─────────────┐                                             │
│  │ forecaster  │                                             │
│  │   -90d      │                                             │
│  └─────────────┘                                             │
│                                                              │
│  Shared Volumes: /data, /configs, /models                   │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Separación de concerns (forecasting vs optimization)
- ✅ No interfiere con forecasters activos
- ✅ Fácil de escalar/modificar independientemente
- ✅ Logs aislados, debugging más fácil
- ✅ Puede correr en horarios de baja carga

**Contras:**
- ❌ Más containers = más recursos RAM/CPU
- ❌ Overhead de orquestación Docker adicional
- ❌ Complejidad de gestión de múltiples servicios

**Esfuerzo:** 2-3 semanas
**Costo:** $0 (opensource)
**Riesgo:** Medio (nueva infraestructura)

**Ejemplo de implementación:**
```python
# src/services/model_optimizer/pipeline.py
class ModelOptimizationPipeline:
    def __init__(self, horizon: str):
        self.horizon = horizon
        self.drift_detector = DataDriftDetector()
        self.perf_monitor = PerformanceMonitor(data_dir=Path("data"))
        self.optimizer = ChronosHyperparameterOptimizer()

    def run(self):
        # 1. Check triggers
        if not self.should_optimize():
            logger.info("No optimization needed")
            return

        # 2. Run optimization
        best_config = self.optimizer.optimize(self.horizon)

        # 3. Validate
        if self.validate_config(best_config):
            # 4. Deploy
            self.deploy_config(best_config)
        else:
            logger.warning("Validation failed - keeping current config")
```

---

### Opción 2: Host-Level Script Orchestrator

**Descripción:**
Script Python que corre en el host (fuera de Docker), ejecutado por cron:
- Monitorea métricas desde archivos compartidos
- Ejecuta optimization dentro de containers existentes
- Más liviano, menos overhead

**Arquitectura:**
```
┌─────────────────────────────────────────────────────────────┐
│                        VPS Host                              │
│  ┌────────────────────────────────────────────────┐         │
│  │  Cron: /scripts/optimize_models.sh (weekly)    │         │
│  │  Ejecuta: python -m optimizer.main             │         │
│  └────────────────────────────────────────────────┘         │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────┐                   │
│  │ Docker Containers (forecasters)       │                   │
│  │ - Léen configs de /configs/*.json    │                   │
│  │ - Escriben métricas a /data/*        │                   │
│  └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Menos containers, menos recursos
- ✅ Más simple de mantener
- ✅ Acceso directo a filesystem del host
- ✅ Fácil debugging (logs en host)

**Contras:**
- ❌ Dependencias Python en host (no containerizado)
- ❌ Menos portable/replicable
- ❌ Puede interferir con containers si no se coordina bien
- ❌ No aprovecha aislamiento Docker

**Esfuerzo:** 1.5-2 semanas
**Costo:** $0
**Riesgo:** Bajo (más simple)

---

### Opción 3: Embedded Logic en Forecasters (Auto-Calibration)

**Descripción:**
Cada forecaster tiene lógica auto-calibración:
- Al inicio de cada run, chequea si necesita recalibrar
- Si detecta drift/degradación, auto-ajusta hiperparámetros
- No requiere servicio separado

**Arquitectura:**
```
┌─────────────────────────────────────────┐
│  forecaster-7d Container                 │
│  ┌────────────────────────────────────┐ │
│  │ 1. Check triggers                  │ │
│  │ 2. If needed: auto-calibrate       │ │
│  │ 3. Run forecast with best config   │ │
│  │ 4. Save metrics                    │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Pros:**
- ✅ Cero overhead de infraestructura
- ✅ Máxima simplicidad
- ✅ Auto-adaptativo en tiempo real
- ✅ No requiere orquestación externa

**Contras:**
- ❌ Forecasters tienen doble responsabilidad (forecast + optimize)
- ❌ Optimización corre durante forecast = más latencia
- ❌ Difícil hacer optimization computacionalmente costosa
- ❌ Si falla optimization, falla el forecast completo

**Esfuerzo:** 1 semana
**Costo:** $0
**Riesgo:** Alto (puede romper forecasting)

---

## Comparación

| Criterio                | Opción 1: Container     | Opción 2: Host Script | Opción 3: Embedded   |
|-------------------------|-------------------------|-----------------------|----------------------|
| **Separación concerns** | ⭐⭐⭐⭐⭐              | ⭐⭐⭐⭐              | ⭐⭐                 |
| **Uso de recursos**     | ⭐⭐                    | ⭐⭐⭐⭐              | ⭐⭐⭐⭐⭐           |
| **Mantenibilidad**      | ⭐⭐⭐⭐                | ⭐⭐⭐⭐⭐            | ⭐⭐⭐               |
| **Portabilidad**        | ⭐⭐⭐⭐⭐              | ⭐⭐                  | ⭐⭐⭐⭐⭐           |
| **Riesgo producción**   | ⭐⭐⭐⭐                | ⭐⭐⭐                 | ⭐                   |
| **Time-to-market**      | 3 semanas               | 2 semanas             | 1 semana             |
| **Escalabilidad**       | ⭐⭐⭐⭐⭐              | ⭐⭐⭐                 | ⭐⭐                 |
| **Debugging**           | ⭐⭐⭐                  | ⭐⭐⭐⭐⭐            | ⭐⭐                 |

---

## Decisión

**Elegimos: Opción 1 - Container Dedicado "Model Optimizer"**

### Justificación:

1. **Separación de concerns es crítica:** Forecasters deben enfocarse en forecasting. Optimization es responsabilidad separada.

2. **Production safety:** Un optimizer independiente puede fallar sin romper forecasts en producción. Con Opción 3, si optimization falla, el forecast falla.

3. **Escalabilidad futura:** Si queremos agregar A/B testing, ensemble optimization, o multi-model selection, un servicio dedicado es mejor arquitectura.

4. **Recursos manejables:** Aunque usa más RAM, el optimizer solo corre semanalmente (o trigger-based), no 24/7. Podemos stop/start el container según necesidad.

5. **Debugging y monitoring:** Logs aislados facilitan troubleshooting. Podemos correr optimizer manualmente para testing.

6. **Team context:** Con 1 desarrollador, la containerización hace el sistema más documentado y reproducible para futuros mantenedores.

### Trade-offs Aceptados:

- ⚠️ **Más complejidad infraestructura** (Mitigación: Docker Compose abstrae orquestación)
- ⚠️ **Mayor uso RAM** (Mitigación: Container solo corre cuando se necesita, no 24/7)
- ⚠️ **Overhead de comunicación** (Mitigación: Comunicación via filesystem compartido, no network)

---

## Consecuencias

### Positivas:

- ✅ **Sistema robusto:** Optimizer puede fallar sin afectar forecasts activos
- ✅ **Testing aislado:** Podemos probar optimization sin riesgo a producción
- ✅ **Monitoring granular:** Métricas específicas de optimization vs forecasting
- ✅ **Escalabilidad:** Fácil agregar features (A/B testing, AutoML, etc.)
- ✅ **Reusabilidad:** Optimizer puede servir múltiples horizontes

### Negativas (Trade-offs aceptados):

- ⚠️ **Mayor complejidad:** Más containers, más moving parts
  - **Mitigación:** Docker Compose simplifica gestión, documentation exhaustiva

- ⚠️ **Overhead de recursos:** +200-400MB RAM cuando corre
  - **Mitigación:** Scheduler inteligente (corre en horarios de baja carga), stop container después de ejecutar

- ⚠️ **Latencia en respuesta:** Optimization no es real-time
  - **Mitigación:** Acceptable trade-off - optimization no necesita ser instantánea

### Riesgos y Mitigaciones:

- **Riesgo 1: Optimizer corrompe configs en producción**
  - **Probabilidad:** Media
  - **Impacto:** Alto
  - **Mitigación:**
    - Atomic file writes con backup
    - Validación exhaustiva antes de deploy
    - Rollback automático si forecasters fallan post-deploy
    - Config versioning (git commit antes de cambiar)

- **Riesgo 2: Optimizer se queda sin memoria durante optimization**
  - **Probabilidad:** Media
  - **Impacto:** Medio
  - **Mitigación:**
    - Límites Docker de memoria (--memory="1g")
    - OOM killer solo afecta optimizer, no forecasters
    - Retry lógica con exponential backoff

- **Riesgo 3: Optimization genera config peor que baseline**
  - **Probabilidad:** Baja (con validación)
  - **Impacto:** Medio
  - **Mitigación:**
    - Validation pipeline compara nuevo config vs actual
    - Deploy solo si mejora >= 5% en métricas clave
    - Shadow mode: generar forecasts en paralelo antes de deploy completo

---

## Plan de Implementación

### Fase 1: Trigger Logic & Monitoring (Semana 1)

**Objetivo:** Sistema que detecta CUÁNDO optimizar

#### Tasks:

- [x] **Ya existe:** `DataDriftDetector` en `src/forex_core/mlops/monitoring.py`
- [x] **Ya existe:** `PerformanceMonitor` en `src/forex_core/mlops/performance_monitor.py`
- [ ] **NEW:** Crear `TriggerManager` que consolida triggers:
  ```python
  class OptimizationTriggerManager:
      def should_optimize(self, horizon: str) -> tuple[bool, str]:
          """
          Returns: (should_optimize: bool, reason: str)
          """
          # Check 1: Performance degradation
          # Check 2: Data drift
          # Check 3: Time-based (min 14 días desde último optimize)
  ```

#### Deliverables:
- `src/forex_core/mlops/triggers.py` (nuevo módulo)
- Unit tests para trigger logic
- Integration con sistemas existentes

---

### Fase 2: Hyperparameter Optimizer (Semana 2)

**Objetivo:** Optimizar hiperparámetros de Chronos

#### Tasks:

- [ ] Crear `ChronosHyperparameterOptimizer`:
  ```python
  class ChronosHyperparameterOptimizer:
      def optimize(self, horizon: str, series: pd.Series) -> OptimizedConfig:
          """
          Busca mejores hiperparámetros:
          - context_length (90, 180, 365 days)
          - num_samples (50, 100, 200)
          - temperature (0.8, 1.0, 1.2)

          Usa grid search simple + cross-validation
          """
  ```

- [ ] **Configuración per-horizon:**
  - `configs/optimizer_params_7d.json`
  - `configs/optimizer_params_15d.json`
  - etc.

#### Deliverables:
- `src/forex_core/optimization/chronos_optimizer.py`
- Config schemas para cada horizonte
- Backtesting framework para validación

---

### Fase 3: Validation Pipeline (Semana 2-3)

**Objetivo:** Validar que nuevo config es MEJOR que actual

#### Tasks:

- [ ] Crear `ConfigValidator`:
  ```python
  class ConfigValidator:
      def validate_against_baseline(
          self,
          new_config: Config,
          current_config: Config,
          validation_window: int = 30
      ) -> ValidationReport:
          """
          Compara performance de new_config vs current_config
          en últimos 30 días de data.

          Aprueba solo si:
          - RMSE mejora >= 5%
          - MAPE mejora >= 3%
          - No aumenta std_dev > 10%
          """
  ```

- [ ] Shadow mode forecasting:
  - Generar forecasts con ambos configs
  - Comparar métricas lado a lado
  - Guardar resultados en `/data/validation/`

#### Deliverables:
- `src/forex_core/optimization/validator.py`
- Validation reports (JSON + HTML)
- Email alerts de resultados

---

### Fase 4: Deployment Pipeline (Semana 3)

**Objetivo:** Deploy seguro de nuevos configs

#### Tasks:

- [ ] Crear `ConfigDeploymentManager`:
  ```python
  class ConfigDeploymentManager:
      def deploy(self, new_config: Config, horizon: str):
          # 1. Backup current config
          self.backup_config(horizon)

          # 2. Write new config atomically
          self.atomic_write(new_config, horizon)

          # 3. Git commit
          self.version_config(horizon, new_config)

          # 4. Trigger forecaster reload (signal or env var)
          self.notify_forecasters(horizon)
  ```

- [ ] Rollback automático:
  - Forecaster detecta si post-deploy hay failures
  - Auto-rollback a config anterior si >3 failures consecutivos

#### Deliverables:
- `src/forex_core/optimization/deployment.py`
- Rollback scripts
- Git integration para config versioning

---

### Fase 5: Docker Integration & Orchestration (Semana 3-4)

**Objetivo:** Integrar todo en container production-ready

#### Tasks:

- [ ] Crear `Dockerfile.optimizer`:
  ```dockerfile
  FROM python:3.12-slim

  # Install dependencies
  COPY requirements.optimizer.txt .
  RUN pip install --no-cache-dir -r requirements.optimizer.txt

  # Copy source
  COPY src/ /app/src/

  # Entrypoint
  CMD ["python", "-m", "services.model_optimizer.main"]
  ```

- [ ] Actualizar `docker-compose.prod.yml`:
  ```yaml
  model-optimizer:
    build:
      context: .
      dockerfile: Dockerfile.optimizer
    container_name: usdclp-model-optimizer
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
      - ./logs:/app/logs
    environment:
      - OPTIMIZATION_MODE=auto
      - SCHEDULE=weekly
    # No restart: corre on-demand o scheduled
  ```

- [ ] Cron job en host:
  ```bash
  # Weekly optimization (Sundays 2am)
  0 2 * * 0 docker-compose -f docker-compose.prod.yml run model-optimizer
  ```

#### Deliverables:
- `Dockerfile.optimizer`
- Docker Compose integration
- Cron setup script
- Documentation

---

### Fase 6: Monitoring & Alerting (Semana 4)

**Objetivo:** Visibility completa del optimization pipeline

#### Tasks:

- [ ] Métricas a trackear:
  - Optimization frequency per horizon
  - Validation success rate
  - Config deployment history
  - Performance before/after optimization
  - Rollback count

- [ ] Email alerts:
  - Optimization triggered (qué trigger activó)
  - Validation passed/failed
  - Config deployed successfully
  - Rollback ejecutado

- [ ] Dashboard integration:
  - Agregar sección "Model Optimization" a `mlops_dashboard.py`
  - Visualizar histórico de optimizations
  - Performance trends pre/post optimization

#### Deliverables:
- `src/forex_core/optimization/monitoring.py`
- Email templates
- Dashboard updates

---

## Métricas de Éxito

### Cómo mediremos si la decisión fue correcta:

#### Métricas Técnicas:

1. **Automation rate:** >= 80% de optimizations sin intervención manual
   - Baseline: 0% (todo manual actualmente)
   - Target: 80% en 3 meses

2. **Performance improvement rate:** >= 60% de optimizations mejoran métricas
   - Métrica: RMSE, MAPE reduction post-optimization
   - Target: 60% success rate

3. **Zero-downtime deployments:** 100% de config deploys sin caída de forecasters
   - Métrica: Forecasters siguen corriendo post-deploy
   - Target: 100%

4. **False positive rate:** <= 10% de optimizations innecesarias
   - Métrica: Optimizations triggered sin degradación real
   - Target: <= 10%

#### Métricas de Calidad:

5. **Forecast accuracy:** Mantener o mejorar RMSE promedio
   - Baseline actual: ~8-12 CLP RMSE (varía por horizonte)
   - Target: Reducir 5-10% en 6 meses

6. **Drift detection latency:** Detectar drift en <= 7 días
   - Métrica: Días desde inicio de drift hasta detección
   - Target: <= 7 días

#### Métricas Operacionales:

7. **Manual intervention frequency:** Reducir intervenciones manuales
   - Baseline: ~2 intervenciones/mes
   - Target: <= 0.5 intervenciones/mes

8. **Time to remediation:** Desde detección hasta config optimizado
   - Métrica: Hours/days
   - Target: <= 24 horas (automático)

---

## Puntos de Revisión

### Checkpoint 1: 2025-01-27 (2 semanas) - MVP Funcional
**Revisar:**
- Trigger logic funcionando
- Optimizer genera configs válidos
- Validación básica implementada

**Criterio de éxito:**
- Puede detectar cuándo optimizar
- Puede generar nuevo config para al menos 1 horizonte
- Tests unitarios pasan

---

### Checkpoint 2: 2025-02-10 (4 semanas) - Production Ready
**Revisar:**
- Docker container deployado
- Validation pipeline completo
- Rollback automático funciona

**Criterio de éxito:**
- Container corre en staging sin errores
- Ha ejecutado al menos 1 optimization completo end-to-end
- Rollback probado y funcional

---

### Checkpoint 3: 2025-03-10 (8 semanas) - Retrospectiva
**Evaluar:**
- Métricas de éxito alcanzadas
- Incidents/issues encontrados
- Lessons learned

**Decisión:**
- ¿Continuar con este approach?
- ¿Necesita ajustes?
- ¿Expandir a features adicionales?

---

## Referencias

### Código Existente Relevante:

- **Drift Detection:** `src/forex_core/mlops/monitoring.py` (DataDriftDetector)
- **Performance Monitoring:** `src/forex_core/mlops/performance_monitor.py`
- **Chronos Model:** `src/forex_core/forecasting/chronos_model.py`
- **Validation Logic:** `scripts/validate_model.py`

### Papers & Resources:

- **Chronos Paper:** "Chronos: Learning the Language of Time Series" (Ansari et al., 2024)
  - https://arxiv.org/abs/2403.07815

- **Drift Detection Methods:**
  - Kolmogorov-Smirnov Test (distribution shift)
  - Population Stability Index (PSI)
  - ADWIN (Adaptive Windowing for data streams)

- **MLOps Best Practices:**
  - Google's "MLOps: Continuous delivery and automation pipelines in ML"
  - "Designing Data-Intensive Applications" - Martin Kleppmann

### Similar Systems:

- **AWS SageMaker Model Monitor:** Automated drift detection + retraining
- **Evidently AI:** Open-source ML monitoring
- **WhyLabs:** Data quality monitoring

---

## Appendix A: Trigger Logic Details

### Trigger 1: Performance Degradation

```python
def check_performance_trigger(horizon: str) -> tuple[bool, str]:
    """
    Trigger optimization if RMSE degraded >15% in last 14 days.
    """
    monitor = PerformanceMonitor(data_dir=Path("data"))
    report = monitor.check_performance(horizon)

    if report.degradation_detected:
        if report.degradation_pct.get("rmse", 0) > 15:
            return True, f"RMSE degraded {report.degradation_pct['rmse']:.1f}%"

    return False, "Performance OK"
```

### Trigger 2: Data Drift

```python
def check_drift_trigger(series: pd.Series) -> tuple[bool, str]:
    """
    Trigger if MEDIUM or HIGH severity drift detected.
    """
    detector = DataDriftDetector(baseline_window=90, test_window=30)
    report = detector.generate_drift_report(series)

    if report.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]:
        return True, f"Drift severity: {report.severity.value}"

    return False, "No significant drift"
```

### Trigger 3: Time-Based Fallback

```python
def check_time_trigger(horizon: str, min_days: int = 14) -> tuple[bool, str]:
    """
    Trigger if no optimization in last N days.
    """
    last_optimization = get_last_optimization_date(horizon)

    if last_optimization is None:
        return True, "Never optimized"

    days_since = (datetime.now() - last_optimization).days

    if days_since >= min_days:
        return True, f"{days_since} days since last optimization"

    return False, f"Last optimized {days_since} days ago"
```

### Combined Trigger Logic

```python
def should_optimize(horizon: str, series: pd.Series) -> tuple[bool, list[str]]:
    """
    Check all triggers and return decision.

    Returns:
        (should_optimize: bool, reasons: list[str])
    """
    reasons = []

    # Check performance
    perf_trigger, perf_reason = check_performance_trigger(horizon)
    if perf_trigger:
        reasons.append(f"Performance: {perf_reason}")

    # Check drift
    drift_trigger, drift_reason = check_drift_trigger(series)
    if drift_trigger:
        reasons.append(f"Drift: {drift_reason}")

    # Check time fallback
    time_trigger, time_reason = check_time_trigger(horizon, min_days=14)
    if time_trigger:
        reasons.append(f"Schedule: {time_reason}")

    # Optimize if ANY trigger fires
    should_opt = len(reasons) > 0

    return should_opt, reasons
```

**Thresholds Recommendation:**
- **Performance:** >= 15% RMSE degradation (configurable)
- **Drift:** Medium or High severity (p-value < 0.05, KS > 0.2)
- **Time:** Minimum 14 days between optimizations (prevent over-optimization)

---

## Appendix B: Hyperparameter Search Space

### Context Length per Horizon

```python
CONTEXT_LENGTH_SEARCH_SPACE = {
    "7d": [90, 180, 270],      # 3, 6, 9 months
    "15d": [90, 180, 365],     # 3, 6, 12 months
    "30d": [180, 365, 540],    # 6, 12, 18 months
    "90d": [365, 540, 730],    # 1, 1.5, 2 years
}
```

### Num Samples

```python
NUM_SAMPLES_SEARCH_SPACE = [50, 100, 200]
# Trade-off: más samples = mejor uncertainty quantification pero +tiempo
```

### Temperature

```python
TEMPERATURE_SEARCH_SPACE = [0.8, 1.0, 1.2]
# Lower = more conservative, higher = more diverse predictions
```

### Grid Search Strategy

```python
def grid_search_optimization(horizon: str, series: pd.Series) -> Config:
    """
    Grid search over hyperparameter space.

    Complejidad: 3 x 3 x 3 = 27 combinaciones
    Tiempo: ~27 * 5s = 135s = 2.25 min (aceptable)
    """
    best_config = None
    best_rmse = float('inf')

    for context in CONTEXT_LENGTH_SEARCH_SPACE[horizon]:
        for num_samples in NUM_SAMPLES_SEARCH_SPACE:
            for temp in TEMPERATURE_SEARCH_SPACE:

                config = Config(
                    context_length=context,
                    num_samples=num_samples,
                    temperature=temp
                )

                # Backtest on last 30 days
                rmse = backtest(config, series, window=30)

                if rmse < best_rmse:
                    best_rmse = rmse
                    best_config = config

    return best_config
```

**Optimización futura:** Bayesian Optimization (Optuna) si grid search es muy lento.

---

## Appendix C: Validation Metrics

### Comparación New Config vs Current Config

```python
class ValidationMetrics:
    """Metrics for comparing two configs."""

    rmse_improvement: float        # % improvement (negative = worse)
    mape_improvement: float
    mae_improvement: float

    ci95_coverage_new: float       # Should be ~0.95
    ci95_coverage_current: float

    bias_new: float                # Should be ~0
    bias_current: float

    inference_time_new: float      # Seconds
    inference_time_current: float

    stability_score: float         # Std dev of errors (lower better)
```

### Approval Criteria

```python
def should_approve_config(metrics: ValidationMetrics) -> bool:
    """
    Approve new config if:
    1. RMSE improves >= 5% OR MAPE improves >= 3%
    2. Std dev doesn't increase > 10%
    3. Inference time doesn't increase > 50%
    4. CI95 coverage >= 0.90
    5. Absolute bias < threshold
    """
    # Criterion 1: Improvement
    improvement = (
        metrics.rmse_improvement <= -5.0 or
        metrics.mape_improvement <= -3.0
    )

    # Criterion 2: Stability
    stable = metrics.stability_score <= 1.10  # Max 10% increase

    # Criterion 3: Performance
    fast_enough = metrics.inference_time_new <= metrics.inference_time_current * 1.5

    # Criterion 4: Coverage
    good_coverage = metrics.ci95_coverage_new >= 0.90

    # Criterion 5: Bias
    low_bias = abs(metrics.bias_new) < 5.0  # Max 5 CLP bias

    return all([improvement, stable, fast_enough, good_coverage, low_bias])
```

---

## Appendix D: Rollback Strategy

### Automatic Rollback Conditions

```python
class RollbackMonitor:
    """
    Monitor forecasters post-deployment and rollback if issues detected.
    """

    def monitor_post_deployment(self, horizon: str, minutes: int = 60):
        """
        Monitor forecaster for N minutes after config deployment.

        Rollback if:
        - 3+ consecutive forecast failures
        - RMSE spike > 50% vs baseline
        - Inference time > 3x baseline
        """
        failures = 0
        baseline_rmse = self.get_baseline_rmse(horizon)

        for _ in range(minutes):
            time.sleep(60)  # Check every minute

            # Check forecaster health
            if not self.is_forecaster_healthy(horizon):
                failures += 1
                logger.warning(f"Forecaster {horizon} unhealthy ({failures}/3)")

                if failures >= 3:
                    logger.error(f"ROLLBACK TRIGGERED: {horizon}")
                    self.rollback_config(horizon)
                    self.alert_team(horizon, "Automatic rollback executed")
                    return False
            else:
                failures = 0  # Reset on success

        logger.info(f"Post-deployment monitoring passed for {horizon}")
        return True
```

### Config Backup & Restore

```python
def backup_config(horizon: str):
    """Backup current config before deployment."""
    current_config = f"configs/chronos_{horizon}.json"
    backup_config = f"configs/backups/chronos_{horizon}_{datetime.now().isoformat()}.json"

    shutil.copy(current_config, backup_config)
    logger.info(f"Config backed up: {backup_config}")

def rollback_config(horizon: str):
    """Restore most recent backup config."""
    backups = sorted(Path("configs/backups").glob(f"chronos_{horizon}_*.json"))

    if not backups:
        logger.error(f"No backup found for {horizon}")
        return False

    latest_backup = backups[-1]
    current_config = f"configs/chronos_{horizon}.json"

    shutil.copy(latest_backup, current_config)
    logger.warning(f"Config rolled back to: {latest_backup.name}")

    # Git commit rollback
    subprocess.run(["git", "add", current_config])
    subprocess.run(["git", "commit", "-m", f"Rollback {horizon} config"])

    return True
```

---

**📝 Documentado por:** Tech Lead Agent
**🤖 Claude Code (Sonnet 4.5)**
