# Model Optimization Module

Automated model optimization pipeline for Chronos forecasting models.

## Overview

This module provides automated optimization capabilities for the USD/CLP forex forecasting system:

- **Trigger Detection:** Automatically detect when optimization is needed
- **Hyperparameter Optimization:** Find optimal Chronos model hyperparameters
- **Configuration Validation:** Ensure new configs improve performance
- **Safe Deployment:** Deploy configs with atomic writes, backups, and rollback

## Quick Start

### Run Optimization for Single Horizon

```python
from pathlib import Path
from services.model_optimizer.pipeline import ModelOptimizationPipeline

# Initialize pipeline
pipeline = ModelOptimizationPipeline(horizon="7d")

# Run optimization
result = pipeline.run()

if result.deployed:
    print(f"Success! RMSE improved {result.validation_report.metrics.rmse_improvement:.1f}%")
```

### Run Optimization for All Horizons

```python
from services.model_optimizer.pipeline import run_optimization_for_all_horizons

results = run_optimization_for_all_horizons()

for horizon, result in results.items():
    print(f"{horizon}: {result.summary}")
```

### CLI Usage

```bash
# Run optimization for specific horizon
python -m services.model_optimizer.cli run --horizon 7d

# Run for all horizons
python -m services.model_optimizer.cli run --all

# Dry run (validation without deployment)
python -m services.model_optimizer.cli run --all --dry-run

# Rollback to previous config
python -m services.model_optimizer.cli rollback 7d

# Show current config status
python -m services.model_optimizer.cli status

# Show optimization history
python -m services.model_optimizer.cli history --horizon 7d
```

## Components

### 1. TriggerManager

Detects when optimization should be triggered.

```python
from forex_core.optimization.triggers import OptimizationTriggerManager

manager = OptimizationTriggerManager(data_dir=Path("data"))
report = manager.should_optimize("7d", usdclp_series)

if report.should_optimize:
    print(f"Optimization triggered: {report.reasons}")
```

**Triggers:**
- **Performance Degradation:** RMSE increased >= 15% vs baseline
- **Data Drift:** Distribution changed (KS test p < 0.05, severity >= MEDIUM)
- **Time-Based:** >= 14 days since last optimization

### 2. ChronosOptimizer

Optimizes Chronos model hyperparameters using grid search.

```python
from forex_core.optimization.chronos_optimizer import ChronosHyperparameterOptimizer

optimizer = ChronosHyperparameterOptimizer(horizon="7d")
best_config = optimizer.optimize(usdclp_series)

print(f"Best RMSE: {best_config.validation_rmse:.2f}")
print(f"Context: {best_config.context_length} days")
print(f"Samples: {best_config.num_samples}")
```

**Hyperparameters Optimized:**
- `context_length`: Historical window size (90, 180, 365 days)
- `num_samples`: Number of probabilistic samples (50, 100, 200)
- `temperature`: Sampling diversity (0.8, 1.0, 1.2)

**Search Method:** Grid search (27 combinations, ~2-5 min)

### 3. ConfigValidator

Validates that new config improves performance.

```python
from forex_core.optimization.validator import ConfigValidator

validator = ConfigValidator(data_dir=Path("data"))
report = validator.validate(new_config, current_config, "7d", series)

if report.approved:
    print("Config approved!")
    print(f"RMSE improvement: {report.metrics.rmse_improvement:.1f}%")
else:
    print("Validation failed:", report.approval_reasons)
```

**Approval Criteria:**
1. RMSE improvement >= 5% OR MAPE improvement >= 3%
2. Std dev increase <= 10%
3. Inference time increase <= 50%
4. CI95 coverage >= 90%
5. Absolute bias < 5 CLP

### 4. DeploymentManager

Safely deploys configurations with rollback capability.

```python
from forex_core.optimization.deployment import ConfigDeploymentManager

manager = ConfigDeploymentManager(config_dir=Path("configs"))
report = manager.deploy(optimized_config, "7d")

if report.success:
    print(f"Deployed! Backup: {report.backup_path}")
else:
    # Rollback
    manager.rollback("7d")
```

**Safety Features:**
- Atomic file writes (no partial writes)
- Timestamped backups
- Git versioning
- Automatic rollback on failure

## Architecture

```
Pipeline Flow:
  Load Data
      ↓
  Check Triggers
      ↓ YES
  Optimize Hyperparameters (grid search)
      ↓
  Validate New Config
      ↓ APPROVED
  Deploy Config (backup → atomic write → git commit)
      ↓
  Record History & Alert
```

## Configuration

### Trigger Thresholds

```python
trigger_manager = OptimizationTriggerManager(
    data_dir=Path("data"),
    performance_threshold=15.0,          # % RMSE degradation
    drift_severity_threshold=DriftSeverity.MEDIUM,
    min_days_between_optimizations=14,  # Min days between optimizations
)
```

### Validation Thresholds

```python
validator = ConfigValidator(
    data_dir=Path("data"),
    rmse_improvement_threshold=5.0,     # Min % RMSE improvement
    mape_improvement_threshold=3.0,     # Min % MAPE improvement
    max_stability_increase=10.0,        # Max % std dev increase
    max_inference_time_increase=50.0,   # Max % inference time increase
    min_ci95_coverage=0.90,             # Min CI95 coverage
    max_bias=5.0,                       # Max bias (CLP)
)
```

### Search Space

```python
from forex_core.optimization.chronos_optimizer import (
    CONTEXT_LENGTH_SEARCH_SPACE,
    NUM_SAMPLES_SEARCH_SPACE,
    TEMPERATURE_SEARCH_SPACE,
)

# Per-horizon context lengths
CONTEXT_LENGTH_SEARCH_SPACE = {
    "7d": [90, 180, 270],
    "15d": [90, 180, 365],
    "30d": [180, 365, 540],
    "90d": [365, 540, 730],
}

NUM_SAMPLES_SEARCH_SPACE = [50, 100, 200]
TEMPERATURE_SEARCH_SPACE = [0.8, 1.0, 1.2]
```

## Data Files

### Config Files

```
/configs/
├── chronos_7d.json       # Current config for 7d horizon
├── chronos_15d.json
├── chronos_30d.json
├── chronos_90d.json
└── backups/              # Timestamped backups
    ├── chronos_7d_20250113_023000.json
    └── ...
```

**Config Format:**
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

### Optimization History

```
/data/optimization_history/
└── history.parquet       # Historical optimization records
```

**Schema:**
```python
{
    "horizon": "7d",
    "optimization_date": datetime,
    "triggered_by": "Performance degradation, Data drift",
    "performance_degradation_pct": 18.5,
    "drift_severity": "MEDIUM",
    "days_since_last": 21,
    "success": True
}
```

## Testing

### Unit Tests

```bash
# Test triggers
pytest tests/unit/test_triggers.py -v

# Test optimizer
pytest tests/unit/test_chronos_optimizer.py -v

# Test validator
pytest tests/unit/test_validator.py -v

# Test deployment
pytest tests/unit/test_deployment.py -v
```

### Integration Tests

```bash
# End-to-end pipeline test
pytest tests/integration/test_optimization_pipeline.py -v
```

## Monitoring

### Metrics Tracked

- Optimization frequency per horizon
- Validation success rate
- Deployment success rate
- Performance improvement (RMSE before/after)
- Trigger frequency (what triggers optimizations)

### Alerts

- Email on optimization triggered
- Email on validation passed/failed
- Email on deployment successful
- Email on rollback executed

## Troubleshooting

### Optimization Too Slow

**Problem:** Grid search takes > 10 minutes

**Solutions:**
1. Reduce search space (fewer hyperparameter options)
2. Switch to random search: `search_method="random"`
3. Reduce `validation_window` (faster backtesting)

### Validation Always Fails

**Problem:** New configs never pass validation

**Solutions:**
1. Review approval criteria thresholds (may be too strict)
2. Check validation window (may be too short)
3. Check if current config is already optimal
4. Review search space (may not include better configs)

### Deployment Fails

**Problem:** Config deployment errors

**Solutions:**
1. Check filesystem permissions
2. Check git repository status
3. Review logs: `logs/model_optimizer.log`
4. Manually rollback: `cli rollback <horizon>`

### False Positive Triggers

**Problem:** Optimization triggered unnecessarily

**Solutions:**
1. Increase `performance_threshold` (less sensitive)
2. Increase `min_days_between_optimizations` (less frequent)
3. Adjust drift detection `alpha` (less sensitive)

## Best Practices

### 1. Start with Dry Run

```bash
# Test pipeline without deployment
python -m services.model_optimizer.cli run --all --dry-run
```

### 2. Monitor Post-Deployment

After deployment, monitor forecaster logs for 60 minutes to ensure stability.

### 3. Version Control

All config changes are automatically git committed. Review commit history:

```bash
git log --oneline configs/
```

### 4. Regular Validation

Periodically check optimization history:

```bash
python -m services.model_optimizer.cli history --limit 20
```

### 5. Adjust Thresholds

Based on results, adjust trigger/validation thresholds in production.

## Future Enhancements

- **Bayesian Optimization:** Smarter search with Optuna
- **A/B Testing:** Shadow mode before full deployment
- **Multi-model Ensemble:** Optimize ensemble weights
- **Drift Prediction:** Proactive optimization
- **Distributed Search:** Parallel grid search

## Documentation

- **ADR:** [docs/decisions/ADR-001-auto-retraining-pipeline.md](../../../docs/decisions/ADR-001-auto-retraining-pipeline.md)
- **Architecture:** [docs/technical/auto-retraining-architecture.md](../../../docs/technical/auto-retraining-architecture.md)
- **Roadmap:** [docs/technical/auto-retraining-roadmap.md](../../../docs/technical/auto-retraining-roadmap.md)
- **Summary:** [docs/AUTO_RETRAINING_SUMMARY.md](../../../docs/AUTO_RETRAINING_SUMMARY.md)

## Support

For questions or issues:
1. Check troubleshooting guide above
2. Review logs: `logs/model_optimizer.log`
3. Check optimization history: `cli history`
4. Consult documentation

---

**Version:** 1.0.0
**Status:** Production Ready (pending Docker integration)
**Maintainer:** Tech Lead Agent
