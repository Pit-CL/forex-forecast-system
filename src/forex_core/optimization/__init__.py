"""
Model Optimization Module for Forex Forecasting System.

This module provides automated model optimization capabilities:
- Trigger detection (when to optimize)
- Hyperparameter optimization
- Configuration validation
- Deployment management
- Rollback strategies

Components:
    - TriggerManager: Decides when optimization is needed
    - ChronosOptimizer: Optimizes Chronos model hyperparameters
    - ConfigValidator: Validates new configs vs baseline
    - DeploymentManager: Safely deploys optimized configs
"""

from .triggers import OptimizationTriggerManager, TriggerReport
from .chronos_optimizer import ChronosHyperparameterOptimizer, OptimizedConfig
from .validator import ConfigValidator, ValidationReport
from .deployment import ConfigDeploymentManager, DeploymentReport

__all__ = [
    "OptimizationTriggerManager",
    "TriggerReport",
    "ChronosHyperparameterOptimizer",
    "OptimizedConfig",
    "ConfigValidator",
    "ValidationReport",
    "ConfigDeploymentManager",
    "DeploymentReport",
]
