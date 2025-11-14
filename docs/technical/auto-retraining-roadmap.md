# Auto-Retraining Pipeline - Implementation Roadmap

**Proyecto:** USD/CLP Forex Forecasting - Model Optimization
**Duración Total:** 3-4 semanas
**Esfuerzo:** 1 desarrollador, ~80-100 horas

---

## Roadmap Incremental

### Fase 1: Trigger Logic & Monitoring (Semana 1)
**Objetivo:** Sistema que detecta CUÁNDO optimizar
**Entregables:** MVP de detección de triggers

#### Tasks

**1.1 Crear TriggerManager (8 horas)**
- [ ] Implementar `OptimizationTriggerManager` clase
- [ ] Integrar con `PerformanceMonitor` (ya existe)
- [ ] Integrar con `DataDriftDetector` (ya existe)
- [ ] Implementar time-based fallback logic
- [ ] Unit tests para cada trigger

**Archivos:**
- ✅ `src/forex_core/optimization/triggers.py` (COMPLETADO)
- ✅ `src/forex_core/optimization/__init__.py` (COMPLETADO)

**Validación:**
```bash
# Test triggers manually
python -m pytest tests/unit/test_triggers.py -v
python examples/test_trigger_detection.py
```

**1.2 Optimization History Tracking (4 horas)**
- [ ] Crear schema para `optimization_history.parquet`
- [ ] Implementar `record_optimization()` method
- [ ] Implementar `get_last_optimization_date()`
- [ ] Test de lectura/escritura de historia

**Schema:**
```python
{
    "horizon": "7d",
    "optimization_date": datetime,
    "triggered_by": "Performance degradation",
    "performance_degradation_pct": 18.5,
    "drift_severity": "MEDIUM",
    "days_since_last": 21,
    "success": True
}
```

**1.3 Integration Testing (4 horas)**
- [ ] Test con data real de USD/CLP
- [ ] Verificar que triggers detectan correctamente
- [ ] Test edge cases (no data, insufficient data, etc.)
- [ ] Documentation de uso

**Milestone 1:** ✅ Sistema detecta cuándo optimizar

---

### Fase 2: Hyperparameter Optimizer (Semana 2)
**Objetivo:** Optimizar hiperparámetros de Chronos
**Entregables:** Optimizer funcional con grid search

#### Tasks

**2.1 Implementar ChronosOptimizer (12 horas)**
- [ ] Crear clase `ChronosHyperparameterOptimizer`
- [ ] Implementar grid search algorithm
- [ ] Implementar backtesting logic
- [ ] Definir search spaces por horizonte
- [ ] Error handling y logging

**Archivos:**
- ✅ `src/forex_core/optimization/chronos_optimizer.py` (COMPLETADO)

**Search Spaces:**
```python
CONTEXT_LENGTH_SEARCH_SPACE = {
    "7d": [90, 180, 270],
    "15d": [90, 180, 365],
    "30d": [180, 365, 540],
    "90d": [365, 540, 730],
}
NUM_SAMPLES_SEARCH_SPACE = [50, 100, 200]
TEMPERATURE_SEARCH_SPACE = [0.8, 1.0, 1.2]
```

**2.2 Backtesting Framework (8 horas)**
- [ ] Implementar walk-forward validation
- [ ] Calcular RMSE, MAPE, MAE por config
- [ ] Handle edge cases (insufficient data, forecast errors)
- [ ] Performance profiling (cuánto demora grid search)

**2.3 Optimization Testing (6 horas)**
- [ ] Test grid search con datos sintéticos
- [ ] Test con USD/CLP real (últimos 2 años)
- [ ] Verificar que encuentra configs razonables
- [ ] Test de performance (debe terminar en < 10 min)
- [ ] Unit tests completos

**Validación:**
```bash
# Test optimization
python examples/test_chronos_optimization.py --horizon 7d
# Expected: ~2-5 min, finds config con RMSE < baseline
```

**Milestone 2:** ✅ Optimizer genera configs optimizados

---

### Fase 3: Validation Pipeline (Semana 2-3)
**Objetivo:** Validar que nuevo config es MEJOR que actual
**Entregables:** Validator production-ready

#### Tasks

**3.1 Implementar ConfigValidator (10 horas)**
- [ ] Crear clase `ConfigValidator`
- [ ] Implementar comparación new vs current config
- [ ] Implementar approval criteria (5 criterios)
- [ ] Calcular todas las métricas de validación
- [ ] Generate detailed validation report

**Archivos:**
- ✅ `src/forex_core/optimization/validator.py` (COMPLETADO)

**Approval Criteria:**
```python
1. RMSE improvement >= 5% OR MAPE improvement >= 3%
2. Std dev increase <= 10%
3. Inference time increase <= 50%
4. CI95 coverage >= 90%
5. Absolute bias < 5 CLP
```

**3.2 Validation Reports (4 horas)**
- [ ] Crear templates para validation reports
- [ ] Generate JSON reports
- [ ] Generate HTML reports (opcional)
- [ ] Email templates para approval/rejection

**3.3 Testing & Edge Cases (6 hours)**
- [ ] Test con configs que pasan validación
- [ ] Test con configs que fallan validación
- [ ] Test initial deployment (no current config)
- [ ] Test con datos edge case
- [ ] Integration tests completos

**Validación:**
```bash
# Test validation
python examples/test_config_validation.py
# Expected: Detailed report con approval decision
```

**Milestone 3:** ✅ Validation pipeline funcional

---

### Fase 4: Deployment Pipeline (Semana 3)
**Objetivo:** Deploy seguro de configs
**Entregables:** Deployment manager con rollback

#### Tasks

**4.1 Implementar DeploymentManager (8 horas)**
- [ ] Crear clase `ConfigDeploymentManager`
- [ ] Implementar backup logic
- [ ] Implementar atomic file writes
- [ ] Implementar rollback functionality
- [ ] Git integration (add, commit)

**Archivos:**
- ✅ `src/forex_core/optimization/deployment.py` (COMPLETADO)

**4.2 Safety Mechanisms (6 horas)**
- [ ] Test atomic writes (no partial files)
- [ ] Test backups (timestamped correctly)
- [ ] Test rollback (restore previous config)
- [ ] Test git commits (proper messages)
- [ ] Concurrent write protection

**4.3 Integration con Forecasters (4 horas)**
- [ ] Modificar forecasters para reload config on change
- [ ] O: Reiniciar forecasters post-deployment
- [ ] Test que forecasters leen nuevo config
- [ ] Test rollback con forecasters activos

**Validación:**
```bash
# Test deployment
python examples/test_deployment.py --horizon 7d
# Verificar:
# - Config file updated
# - Backup created
# - Git commit exists
# - Rollback works
```

**Milestone 4:** ✅ Deployment seguro y rollback funcional

---

### Fase 5: Docker Integration & Orchestration (Semana 3-4)
**Objetivo:** Containerizar todo el pipeline
**Entregables:** Container production-ready

#### Tasks

**5.1 Crear Dockerfile (4 horas)**
- [ ] Dockerfile.optimizer
- [ ] Requirements.optimizer.txt
- [ ] Entrypoint script
- [ ] Build y test local

**Dockerfile.optimizer:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.optimizer.txt .
RUN pip install --no-cache-dir -r requirements.optimizer.txt

# Copy source
COPY src/ /app/src/
COPY configs/ /app/configs/

# Set environment
ENV PYTHONPATH=/app

# Entrypoint
CMD ["python", "-m", "forex_core.optimization.cli", "run"]
```

**5.2 Docker Compose Integration (4 horas)**
- [ ] Añadir service `model-optimizer` a docker-compose.prod.yml
- [ ] Configurar volumes compartidos
- [ ] Configurar environment variables
- [ ] Configurar resource limits (memory, CPU)

**docker-compose.prod.yml:**
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
    - ENVIRONMENT=production
    - OPTIMIZATION_MODE=auto
  mem_limit: 1g
  cpus: 2.0
```

**5.3 CLI Interface (6 horas)**
- [ ] Crear CLI con typer
- [ ] Comandos: `run`, `rollback`, `status`, `history`
- [ ] Help messages y documentation
- [ ] Test CLI en container

**CLI:**
```bash
# Run optimization for all horizons
python -m forex_core.optimization.cli run --all

# Run for specific horizon
python -m forex_core.optimization.cli run --horizon 7d

# Rollback specific horizon
python -m forex_core.optimization.cli rollback --horizon 7d

# Show optimization history
python -m forex_core.optimization.cli history --horizon 7d

# Check status
python -m forex_core.optimization.cli status
```

**5.4 Cron Setup (2 horas)**
- [ ] Script para instalar cron job
- [ ] Configurar horario (Sundays 2am Chile time)
- [ ] Test manual execution
- [ ] Test scheduled execution

**Cron:**
```bash
# /etc/cron.d/model-optimizer
0 2 * * 0 cd /path/to/forex-forecast-system && docker-compose -f docker-compose.prod.yml run model-optimizer
```

**Validación:**
```bash
# Build container
docker-compose build model-optimizer

# Test manual run
docker-compose run model-optimizer run --horizon 7d

# Check logs
docker logs usdclp-model-optimizer
```

**Milestone 5:** ✅ Container deployado y funcionando

---

### Fase 6: Monitoring & Alerting (Semana 4)
**Objetivo:** Visibility completa del pipeline
**Entregables:** Monitoring y alerts funcionales

#### Tasks

**6.1 Optimization Metrics (4 horas)**
- [ ] Tracking de optimization frequency
- [ ] Tracking de validation success rate
- [ ] Tracking de deployment success rate
- [ ] Tracking de performance improvements
- [ ] Save metrics to parquet

**6.2 Dashboard Integration (6 horas)**
- [ ] Agregar sección a `mlops_dashboard.py`
- [ ] Visualizar optimization history
- [ ] Performance trends (before/after optimization)
- [ ] Trigger frequency chart
- [ ] Success rate metrics

**Dashboard Sections:**
```
Model Optimization Dashboard
├── Optimization Frequency (per horizon)
├── Validation Success Rate (rolling 30d)
├── Performance Improvements (RMSE before/after)
├── Last Optimization Details
└── Trigger History (what triggered optimizations)
```

**6.3 Email Alerts (4 horas)**
- [ ] Email template: Optimization triggered
- [ ] Email template: Validation passed/failed
- [ ] Email template: Deployment successful
- [ ] Email template: Rollback executed
- [ ] Integration con sistema email existente

**Email Templates:**
```
Subject: [Model Optimizer] Optimization Triggered for 7d

Horizon: 7d
Triggered by:
- Performance degradation: RMSE +18.5%
- Data drift: MEDIUM severity

Optimization started at 2025-01-13 02:00:00
Expected completion: ~5 minutes

---
Subject: [Model Optimizer] Validation PASSED for 7d

New config approved for deployment:
- RMSE improvement: +12.3%
- Context length: 180d → 270d
- Num samples: 100 → 200

Deployment will proceed automatically.
```

**6.4 Integration Testing (4 horas)**
- [ ] Test end-to-end pipeline con alertas
- [ ] Verificar que emails se envían correctamente
- [ ] Test dashboard visualizations
- [ ] Test metrics tracking
- [ ] Documentation final

**Validación:**
```bash
# Run full pipeline con monitoring
docker-compose run model-optimizer run --all --verbose

# Check dashboard
python scripts/mlops_dashboard.py

# Verify emails sent
# Check inbox para optimization alerts
```

**Milestone 6:** ✅ Monitoring y alerting completos

---

## Post-Implementation Tasks

### Documentation (Semana 4)
- [ ] README para module optimization
- [ ] API documentation (docstrings completos)
- [ ] User guide para operators
- [ ] Troubleshooting guide
- [ ] Architecture diagrams (Mermaid o ASCII)

### Testing & QA (Semana 4)
- [ ] Integration tests end-to-end
- [ ] Load testing (performance bajo carga)
- [ ] Chaos testing (qué pasa si falla cada componente)
- [ ] Security review
- [ ] Code review

### Deployment (Semana 4)
- [ ] Deploy a staging environment
- [ ] Run optimization en staging (dry run)
- [ ] Monitor por 1 semana en staging
- [ ] Deploy a production
- [ ] Post-deployment monitoring (2 semanas)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Grid search demasiado lento** | MEDIUM | MEDIUM | • Fallback a random search<br>• Reduce search space<br>• Parallel grid search (futuro) |
| **Optimizer corrompe configs** | LOW | HIGH | • Atomic writes<br>• Backups automáticos<br>• Rollback automático |
| **Validation muy restrictiva** | MEDIUM | MEDIUM | • Ajustar thresholds basado en resultados<br>• Manual override capability |
| **Cron job no ejecuta** | LOW | MEDIUM | • Logging extensivo<br>• Email alerts si no ejecuta<br>• Manual trigger capability |
| **Git conflicts en configs** | LOW | LOW | • Single source of truth (optimizer writes)<br>• Config files simple (JSON) |
| **OOM durante optimization** | MEDIUM | MEDIUM | • Memory limits en Docker<br>• Reduce num_samples si OOM<br>• Monitor memory usage |

---

## Success Metrics

### Technical KPIs

| Metric | Baseline | Target (3 months) | Measurement |
|--------|----------|-------------------|-------------|
| **Automation rate** | 0% | 80% | % optimizations sin intervención manual |
| **Validation success** | N/A | >= 60% | % validations que aprueban nuevo config |
| **RMSE improvement** | 0% | 5-10% | Avg RMSE reduction post-optimization |
| **Zero-downtime deployments** | N/A | 100% | % deployments sin downtime |
| **False positive triggers** | N/A | <= 10% | % triggers innecesarios |

### Operational KPIs

| Metric | Baseline | Target (6 months) |
|--------|----------|-------------------|
| **Manual interventions** | 2/month | <= 0.5/month |
| **Drift detection latency** | N/A | <= 7 days |
| **Time to remediation** | N/A | <= 24 hours |
| **Forecast accuracy** | ~8-12 RMSE | ~7-11 RMSE |

---

## Estimated Effort

| Fase | Hours | Días (8h/día) |
|------|-------|---------------|
| Fase 1: Triggers | 16h | 2 días |
| Fase 2: Optimizer | 26h | 3.25 días |
| Fase 3: Validator | 20h | 2.5 días |
| Fase 4: Deployment | 18h | 2.25 días |
| Fase 5: Docker | 16h | 2 días |
| Fase 6: Monitoring | 18h | 2.25 días |
| **Subtotal Implementation** | **114h** | **14.25 días** |
| Documentation | 12h | 1.5 días |
| Testing & QA | 16h | 2 días |
| Deployment | 8h | 1 día |
| **Total** | **150h** | **~19 días** |

**Timeline:** 3-4 semanas (considerando testing, debugging, ajustes)

---

## Next Steps

### Immediate (Week 1)
1. ✅ Review y aprobación del ADR
2. ✅ Review de arquitectura propuesta
3. [ ] Setup development environment
4. [ ] Comenzar Fase 1: TriggerManager

### Short-term (Week 2-3)
5. [ ] Implementar Fase 2-4
6. [ ] Testing iterativo
7. [ ] Ajustes basados en resultados

### Medium-term (Week 4)
8. [ ] Docker integration
9. [ ] Monitoring & alerting
10. [ ] Staging deployment
11. [ ] Production deployment

### Long-term (Months 2-3)
12. [ ] Monitor performance en producción
13. [ ] Ajustar thresholds basado en experiencia
14. [ ] Implement Phase 2 features (Bayesian opt, A/B testing)

---

**Documentado por:** Tech Lead Agent
**Última actualización:** 2025-01-13
**Versión:** 1.0
