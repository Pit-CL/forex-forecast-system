"""
MLOps utilities for model monitoring and management.

This package provides tools for production ML operations:
- Data drift detection
- Model performance monitoring
- Statistical tests for distribution changes
- Prediction tracking and out-of-sample evaluation
- System readiness validation for feature rollout
"""

from .monitoring import (
    DataDriftDetector,
    DriftReport,
    DriftSeverity,
    DriftTestResult,
)

# Try to import optional components
_all_exports = [
    "DataDriftDetector",
    "DriftReport",
    "DriftSeverity",
    "DriftTestResult",
]

try:
    from .tracking import PredictionTracker
    _all_exports.append("PredictionTracker")
except ImportError:
    pass

try:
    from .readiness import (
        ChronosReadinessChecker,
        ReadinessReport,
        ReadinessLevel,
    )
    _all_exports.extend([
        "ChronosReadinessChecker",
        "ReadinessReport",
        "ReadinessLevel",
    ])
except ImportError:
    pass

try:
    from .drift_trends import (
        DriftTrendAnalyzer,
        DriftTrendReport,
        DriftTrend,
    )
    _all_exports.extend([
        "DriftTrendAnalyzer",
        "DriftTrendReport",
        "DriftTrend",
    ])
except ImportError:
    pass

try:
    from .validation import (
        WalkForwardValidator,
        ValidationReport,
        ValidationMetrics,
        ValidationMode,
    )
    _all_exports.extend([
        "WalkForwardValidator",
        "ValidationReport",
        "ValidationMetrics",
        "ValidationMode",
    ])
except ImportError:
    pass

try:
    from .regime_detector import (
        MarketRegimeDetector,
        MarketRegime,
        RegimeReport,
        RegimeSignals,
    )
    _all_exports.extend([
        "MarketRegimeDetector",
        "MarketRegime",
        "RegimeReport",
        "RegimeSignals",
    ])
except ImportError:
    pass

try:
    from .performance_monitor import (
        PerformanceMonitor,
        DegradationReport,
        PerformanceStatus,
        PerformanceMetrics,
        PerformanceBaseline,
    )
    _all_exports.extend([
        "PerformanceMonitor",
        "DegradationReport",
        "PerformanceStatus",
        "PerformanceMetrics",
        "PerformanceBaseline",
    ])
except ImportError:
    pass

__all__ = _all_exports
