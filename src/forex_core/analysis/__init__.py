"""
Analysis modules for forex forecasting.

This package provides technical, fundamental, and macroeconomic analysis
capabilities for currency pair forecasting.

Modules:
    - technical: Technical indicators (RSI, MACD, Bollinger Bands, MA, etc.)
    - fundamental: Fundamental analysis and quantitative factors
    - macro: Macroeconomic analysis and risk regime detection
"""

from .technical import (
    compute_technicals,
    calculate_rsi,
    calculate_macd,
)

from .fundamental import (
    QuantFactor,
    build_quant_factors,
    macro_events_table,
    extract_quant_factors,
)

from .macro import (
    RiskGauge,
    compute_risk_gauge,
)

__all__ = [
    # Technical
    "compute_technicals",
    "calculate_rsi",
    "calculate_macd",
    # Fundamental
    "QuantFactor",
    "build_quant_factors",
    "macro_events_table",
    "extract_quant_factors",
    # Macro
    "RiskGauge",
    "compute_risk_gauge",
]
