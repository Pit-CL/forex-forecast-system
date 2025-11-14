"""
Feature engineering module for USD/CLP forecasting.

Generates 50+ features from raw data for XGBoost and SARIMAX models.
"""

from forex_core.features.feature_engineer import (
    add_copper_features,
    add_derived_features,
    add_lagged_features,
    add_macro_features,
    add_technical_indicators,
    engineer_features,
    validate_features,
)

__all__ = [
    "engineer_features",
    "add_lagged_features",
    "add_technical_indicators",
    "add_copper_features",
    "add_macro_features",
    "add_derived_features",
    "validate_features",
]
