"""
Services package for forex-forecast-system.

This package contains thin service wrappers around the forex_core library.
Each service provides specific configuration and orchestration for different
forecast horizons and report types.

Available services:
- forecaster_7d: Short-term (7-day) daily forex forecasting
- forecaster_12m: Long-term (12-month) monthly forex forecasting
- importer_report: Comprehensive monthly macro-economic report for importers
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
