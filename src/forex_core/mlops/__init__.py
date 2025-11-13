"""
MLOps utilities for model monitoring and management.

This package provides tools for production ML operations:
- Data drift detection
- Model performance monitoring
- Statistical tests for distribution changes
- Prediction tracking and out-of-sample evaluation
"""

from .monitoring import (
    DataDriftDetector,
    DriftReport,
    DriftSeverity,
    DriftTestResult,
)

# Try to import PredictionTracker, but don't fail if dependencies not available
try:
    from .tracking import PredictionTracker
    __all__ = [
        "DataDriftDetector",
        "DriftReport",
        "DriftSeverity",
        "DriftTestResult",
        "PredictionTracker",
    ]
except ImportError as e:
    # PredictionTracker not available, but core drift detection still works
    __all__ = [
        "DataDriftDetector",
        "DriftReport",
        "DriftSeverity",
        "DriftTestResult",
    ]
