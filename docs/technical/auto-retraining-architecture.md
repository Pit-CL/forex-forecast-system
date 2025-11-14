# Auto-Retraining Pipeline Architecture

**Sistema:** USD/CLP Forex Forecasting - Model Optimization
**Fecha:** 2025-01-13
**Versión:** 1.0

---

## 1. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         VPS Vultr (Production)                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FORECASTER CONTAINERS (4x)                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ 7d       │  │ 15d      │  │ 30d      │  │ 90d      │            │   │
│  │  │ Chronos  │  │ Chronos  │  │ Chronos  │  │ Chronos  │            │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │       │             │             │             │                    │   │
│  │       │ Read        │             │             │                    │   │
│  │       ▼             ▼             ▼             ▼                    │   │
│  │  ┌──────────────────────────────────────────────────┐               │   │
│  │  │   Shared Configs: /configs/chronos_*.json        │               │   │
│  │  └──────────────────────────────────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                ▲                                             │
│                                │ Update configs                              │
│                                │                                             │
│  ┌─────────────────────────────┴───────────────────────────────────────┐   │
│  │              MODEL OPTIMIZER CONTAINER (on-demand)                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │  OptimizationPipeline                                      │     │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │     │   │
│  │  │  │ 1. Triggers  │→ │ 2. Optimize  │→ │ 3. Validate  │     │     │   │
│  │  │  │ - Perf Degrad│  │ - Grid Search│  │ - Backtest   │     │     │   │
│  │  │  │ - Drift      │  │ - Find Best  │  │ - Compare    │     │     │   │
│  │  │  │ - Time-based │  │   Hyperparam │  │ - Approve    │     │     │   │
│  │  │  └──────────────┘  └──────────────┘  └──────┬───────┘     │     │   │
│  │  │                                              │             │     │   │
│  │  │                                              ▼             │     │   │
│  │  │                                      ┌──────────────┐     │     │   │
│  │  │                                      │ 4. Deploy    │     │     │   │
│  │  │                                      │ - Backup     │     │     │   │
│  │  │                                      │ - Atomic     │     │     │   │
│  │  │                                      │ - Git commit │     │     │   │
│  │  │                                      │ - Notify     │     │     │   │
│  │  │                                      └──────────────┘     │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  Inputs:                           Outputs:                         │   │
│  │  • Historical data (/data/warehouse)  • Optimized configs           │   │
│  │  • Performance metrics (/data/predictions)  • Validation reports    │   │
│  │  • Drift history (/data/drift_history)  • Optimization history      │   │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    SHARED VOLUMES (Persistent)                        │  │
│  │  /data/         - Warehouse, predictions, drift history               │  │
│  │  /configs/      - Model configurations (versioned)                    │  │
│  │  /logs/         - Application logs                                    │  │
│  │  /output/       - Forecast outputs                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   SCHEDULER (Cron on Host)                            │  │
│  │  • Weekly optimization: Sundays 2am Chile time                        │  │
│  │  • Command: docker-compose run model-optimizer                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 TriggerManager

**Responsabilidad:** Detectar CUÁNDO optimizar

**Inputs:**
- Historical USD/CLP series
- Performance metrics (predictions.parquet)
- Drift history
- Optimization history

**Outputs:**
- `TriggerReport` (should_optimize: bool, reasons: list)

**Triggers:**
1. **Performance Degradation:** RMSE degraded >= 15% vs baseline (últimos 14d vs últimos 60d)
2. **Data Drift:** KS test p-value < 0.05, severity >= MEDIUM
3. **Time-Based Fallback:** >= 14 días desde última optimización

**Error Handling:**
- Si fallan monitors, log warning y continuar con otros triggers
- Si todos fallan, usar solo time-based trigger

---

### 2.2 ChronosOptimizer

**Responsabilidad:** Encontrar hiperparámetros óptimos

**Inputs:**
- Horizon (7d, 15d, 30d, 90d)
- Historical series
- Search space configs

**Outputs:**
- `OptimizedConfig` con:
  - context_length, num_samples, temperature
  - validation_rmse, validation_mape
  - search_iterations, optimization_time

**Algoritmo:**
```python
for context in [90, 180, 365]:
    for num_samples in [50, 100, 200]:
        for temp in [0.8, 1.0, 1.2]:
            # Backtest on last 30 days
            forecast = chronos(series, context, num_samples, temp)
            rmse = compare_vs_actual(forecast, actual)
            if rmse < best_rmse:
                best_config = (context, num_samples, temp)
return best_config
```

**Complejidad:**
- Grid search: 3 x 3 x 3 = 27 evaluations
- Tiempo estimado: ~27 * 5s = 135s (~2 min)

**Error Handling:**
- Si backtest falla para un config, marcar como inf RMSE y continuar
- Si todos fallan, raise RuntimeError

---

### 2.3 ConfigValidator

**Responsabilidad:** Validar que nuevo config ES MEJOR que actual

**Inputs:**
- new_config (OptimizedConfig)
- current_config (OptimizedConfig o None)
- Horizon
- Historical series

**Outputs:**
- `ValidationReport` (approved: bool, metrics, reasons)

**Validation Criteria:**
```python
def approve(new, current):
    # Criterion 1: Performance improvement
    improved = (
        rmse_improvement >= 5% OR
        mape_improvement >= 3%
    )

    # Criterion 2: Stability (std dev)
    stable = std_new / std_current <= 1.10  # Max 10% increase

    # Criterion 3: Inference time
    fast = time_new / time_current <= 1.50  # Max 50% slower

    # Criterion 4: CI95 coverage
    good_coverage = ci95_coverage >= 0.90

    # Criterion 5: Low bias
    low_bias = abs(mean_error) < 5.0  # Max 5 CLP bias

    return improved AND stable AND fast AND good_coverage AND low_bias
```

**Error Handling:**
- Si current_config es None, auto-approve (initial deployment)
- Si backtest falla, reject con error message

---

### 2.4 DeploymentManager

**Responsabilidad:** Deploy seguro de configs

**Inputs:**
- config (OptimizedConfig)
- horizon

**Outputs:**
- `DeploymentReport` (success: bool, backup_path, git_hash)

**Proceso:**
```python
def deploy(config, horizon):
    # 1. Backup current config
    backup_path = backup_config(horizon)

    # 2. Write new config atomically
    temp_path = write_to_temp(config)
    atomic_move(temp_path, target_path)

    # 3. Git commit (optional)
    git_add(target_path)
    git_commit("Deploy optimized config for {horizon}")

    # 4. Notify (optional)
    send_email(f"Config deployed for {horizon}")

    return DeploymentReport(success=True, backup_path, git_hash)
```

**Safety Features:**
- **Atomic writes:** Write to .tmp, then rename (prevents partial writes)
- **Backups:** Timestamped backups antes de cada deployment
- **Git versioning:** Cada config change es un commit
- **Rollback:** Restaurar último backup si deployment falla

**Error Handling:**
- Si backup falla, abort deployment
- Si atomic write falla, no se mueve el temp file
- Si git commit falla, log warning pero deployment continúa

---

## 3. Data Flow

```
┌──────────────┐
│ Daily Cron   │
│ (Sundays 2am)│
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 1. Load Historical Data                  │
│    • USD/CLP series from warehouse       │
│    • Performance metrics from predictions│
│    • Drift history                       │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 2. Check Triggers (per horizon)          │
│    • Performance: RMSE degraded?         │
│    • Drift: Distribution changed?        │
│    • Time: 14+ days since last?          │
└──────┬───────────────────────────────────┘
       │
       ▼
   ┌───────────┐
   │ Optimize? │  NO → Exit (log "No optimization needed")
   └───┬───────┘
       │ YES
       ▼
┌──────────────────────────────────────────┐
│ 3. Hyperparameter Optimization           │
│    • Grid search over search space       │
│    • Backtest each config on last 30d    │
│    • Select best RMSE                    │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 4. Validation                             │
│    • Compare new vs current config       │
│    • Check all approval criteria         │
│    • Generate ValidationReport           │
└──────┬───────────────────────────────────┘
       │
       ▼
   ┌───────────┐
   │ Approved? │  NO → Exit (log "Validation failed")
   └───┬───────┘
       │ YES
       ▼
┌──────────────────────────────────────────┐
│ 5. Deployment                             │
│    • Backup current config               │
│    • Write new config atomically         │
│    • Git commit                          │
│    • Email notification                  │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ 6. Record History                         │
│    • Save optimization record            │
│    • Update metrics dashboard            │
└──────────────────────────────────────────┘
```

---

## 4. Failure Modes & Resilience

| Failure Scenario | Impact | Detection | Mitigation |
|------------------|--------|-----------|------------|
| **Optimizer OOM (out of memory)** | Optimization fails | Docker memory limit | • Set --memory="1g" limit<br>• OOM kills only optimizer, not forecasters<br>• Retry with random search (less memory) |
| **Grid search too slow** | Optimization timeout | Timeout after 10 min | • Fallback to random search<br>• Reduce search space<br>• Log warning, continue with current config |
| **Validation fails (new config worse)** | No deployment | ValidationReport.approved=False | • Keep current config<br>• Log reason<br>• Email alert with details |
| **Deployment corrupts config file** | Forecasters fail to load config | Atomic write failed | • Restore from backup automatically<br>• Config backup before every deployment |
| **Git commit fails** | No version control | subprocess.CalledProcessError | • Log warning<br>• Deployment continues (git is optional)<br>• Manual git recovery later |
| **Forecaster reads config mid-write** | Forecaster gets partial config | Race condition | • Atomic writes prevent this<br>• Config loaded once at startup |
| **Optimizer runs during forecast** | Resource contention (CPU/RAM) | N/A | • Schedule optimizer at 2am (low traffic)<br>• Set CPU limits on optimizer |

---

## 5. Monitoring & Alerting

### Metrics to Track

**Optimization Metrics:**
- Optimization frequency per horizon (should be ~weekly)
- Validation success rate (target: >= 60%)
- Deployment success rate (target: 100%)
- Average optimization time (baseline: ~2-5 min)

**Performance Metrics:**
- RMSE before/after optimization
- % improvement in RMSE (target: >= 5%)
- Config stability (how often configs change)

**System Metrics:**
- Optimizer container memory usage
- Optimizer execution time
- Rollback count (target: 0)

### Alerts

| Condition | Severity | Action |
|-----------|----------|--------|
| Validation fails 3+ times consecutively | MEDIUM | Email alert: "Optimization not finding better configs" |
| Deployment fails | HIGH | Email alert: "Config deployment failed - manual intervention needed" |
| Rollback executed | HIGH | Email + Slack: "Config rolled back - investigate root cause" |
| Optimization time > 15 min | MEDIUM | Email: "Optimization slow - consider reducing search space" |
| No optimization in 30+ days | LOW | Email: "No triggers detected - system may be stale" |

---

## 6. Configuration Management

### Config File Format

```json
{
  "horizon": "7d",
  "context_length": 180,
  "num_samples": 100,
  "temperature": 1.0,
  "validation_rmse": 8.45,
  "validation_mape": 0.89,
  "validation_mae": 6.73,
  "search_iterations": 27,
  "optimization_time_seconds": 142.3,
  "timestamp": "2025-01-13T14:32:00"
}
```

### Config Locations

```
/configs/
├── chronos_7d.json       # Current config for 7d
├── chronos_15d.json
├── chronos_30d.json
├── chronos_90d.json
└── backups/              # Timestamped backups
    ├── chronos_7d_20250113_023000.json
    ├── chronos_7d_20250106_023000.json
    └── ...
```

### Git Versioning

Every config deployment creates a git commit:

```bash
commit abc123def456
Author: Model Optimizer <optimizer@forex-system.com>
Date:   Sun Jan 13 02:30:00 2025 -0300

    Deploy optimized config for 7d

    RMSE: 8.45
    Context: 180d
    Samples: 100
    Temperature: 1.0
    Optimized: 2025-01-13T02:30:00
```

---

## 7. Rollback Strategy

### Automatic Rollback Triggers

```python
class PostDeploymentMonitor:
    """Monitor forecasters after config deployment."""

    def monitor(self, horizon: str, duration_minutes: int = 60):
        failures = 0

        for _ in range(duration_minutes):
            time.sleep(60)  # Check every minute

            # Check forecaster health
            if not is_forecaster_healthy(horizon):
                failures += 1
                logger.warning(f"Forecaster {horizon} unhealthy ({failures}/3)")

                if failures >= 3:
                    logger.error(f"ROLLBACK TRIGGERED: {horizon}")
                    self.rollback(horizon)
                    self.alert_team(horizon, "Automatic rollback executed")
                    return False
            else:
                failures = 0  # Reset on success

        logger.info(f"Post-deployment monitoring passed for {horizon}")
        return True
```

### Manual Rollback

```bash
# Via deployment manager
python -m forex_core.optimization.cli rollback --horizon 7d

# Via Docker
docker-compose run model-optimizer rollback --horizon 7d
```

---

## 8. Security & Safety

### Docker Security

```yaml
# docker-compose.prod.yml
model-optimizer:
  security_opt:
    - no-new-privileges:true  # Prevent privilege escalation
  read_only: false  # Need write for /data, /configs
  tmpfs:
    - /tmp  # Ephemeral temp storage
  mem_limit: 1g  # Memory limit
  cpus: 2.0  # CPU limit
```

### File Permissions

```bash
/configs/
├── chronos_7d.json       # 644 (read-write owner, read others)
└── backups/              # 755 (read-write owner, read-exec others)
```

### Git Safety

- No force push allowed
- Main branch protected
- Config commits signed (optional)

---

## 9. Performance Estimates

### Resource Usage

| Component | CPU | RAM | Disk I/O |
|-----------|-----|-----|----------|
| Optimizer (idle) | 0% | 0 MB | 0 |
| Optimizer (running) | 100-200% | 600-800 MB | Low |
| Forecaster impact | +5-10% | +50 MB | Low |

### Timing

| Operation | Duration |
|-----------|----------|
| Trigger check | ~5-10s |
| Grid search (27 configs) | ~2-5 min |
| Validation | ~1-2 min |
| Deployment | ~5-10s |
| **Total optimization** | **~3-8 min** |

### Frequency

- **Scheduled:** Weekly (Sundays 2am)
- **Trigger-based:** As needed (max once per 14 days per horizon)
- **Manual:** On-demand via CLI

---

## 10. Future Enhancements

### Phase 2 (Nice-to-have)

- **Bayesian Optimization:** Replace grid search with Optuna for smarter search
- **A/B Testing:** Run new config in shadow mode before full deployment
- **Multi-model Ensemble:** Optimize ensemble weights, not just Chronos
- **Auto-scaling:** Adjust search space based on available resources
- **Drift Prediction:** Predict when drift will occur (proactive optimization)

### Phase 3 (Advanced)

- **Reinforcement Learning:** Learn optimal trigger thresholds over time
- **Cost-aware Optimization:** Factor in inference cost vs accuracy
- **Distributed Optimization:** Parallelize grid search across multiple workers
- **AutoML Integration:** Integrate with AutoML frameworks (AutoGluon, FLAML)

---

**Documentado por:** Tech Lead Agent
**Última actualización:** 2025-01-13
**Versión:** 1.0
