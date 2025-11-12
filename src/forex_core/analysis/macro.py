"""
Macroeconomic analysis and risk regime detection.

This module provides functions for analyzing global macroeconomic conditions
and identifying risk-on/risk-off market regimes based on key indicators:
- DXY (US Dollar Index): Safe-haven flows
- VIX (Volatility Index): Market fear gauge
- EEM (Emerging Markets ETF): EM risk appetite

Risk regime detection helps contextualize forex movements within broader
market sentiment and capital flow dynamics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..data.loader import DataBundle


@dataclass
class RiskGauge:
    """
    Market risk regime assessment based on macro indicators.

    The risk regime is determined by a scoring system:
    - Each of DXY, VIX, EEM contributes +1 (risk-on) or -1 (risk-off)
    - Score >= 2: Risk-on (strong risk appetite, EM supportive)
    - Score <= -2: Risk-off (risk aversion, EM negative)
    - Score in [-1, 1]: Neutral (mixed signals)

    Attributes:
        dxy_change: % change in DXY over lookback period (5 days).
                    Negative = risk-on (USD weakening).
        vix_change: % change in VIX over lookback period (5 days).
                    Negative = risk-on (volatility declining).
        eem_change: % change in EEM over lookback period (5 days).
                    Positive = risk-on (EM gaining).
        regime: Risk regime classification ("Risk-on", "Risk-off", "Neutral").

    Example:
        >>> gauge = RiskGauge(
        ...     dxy_change=-1.5,  # USD weakening
        ...     vix_change=-8.2,   # Volatility dropping
        ...     eem_change=2.3,    # EM rallying
        ...     regime="Risk-on"
        ... )
    """
    dxy_change: float
    vix_change: float
    eem_change: float
    regime: str


def compute_risk_gauge(bundle: DataBundle) -> RiskGauge:
    """
    Compute market risk regime from macroeconomic indicators.

    This function analyzes recent changes in key risk indicators to determine
    the prevailing market regime. The regime affects emerging market currencies
    like CLP through capital flow dynamics.

    Risk-on characteristics:
        - USD weakening (DXY down) - capital flowing to higher-yielding assets
        - Volatility declining (VIX down) - reduced fear in markets
        - EM outperforming (EEM up) - risk appetite for emerging markets

    Risk-off characteristics:
        - USD strengthening (DXY up) - safe-haven demand
        - Volatility rising (VIX up) - market stress and uncertainty
        - EM underperforming (EEM down) - capital fleeing to safety

    Scoring algorithm:
        1. Calculate 5-day % change for each indicator
        2. Assign score for each:
           - DXY: -1 if down (risk-on), +1 if up (risk-off)
           - VIX: -1 if down (risk-on), +1 if up (risk-off)
           - EEM: +1 if up (risk-on), -1 if down (risk-off)
        3. Sum scores (range: -3 to +3)
        4. Classify regime:
           - Score >= 2: "Risk-on"
           - Score <= -2: "Risk-off"
           - Otherwise: "Neutral"

    Args:
        bundle: DataBundle containing dxy_series, vix_series, eem_series.

    Returns:
        RiskGauge with percentage changes and regime classification.

    Example:
        >>> from forex_core.data.loader import load_data
        >>> bundle = load_data()
        >>> gauge = compute_risk_gauge(bundle)
        >>> print(f"Regime: {gauge.regime}")
        >>> print(f"DXY: {gauge.dxy_change:+.2f}%")
        >>> print(f"VIX: {gauge.vix_change:+.2f}%")
        >>> print(f"EEM: {gauge.eem_change:+.2f}%")

    Notes:
        - Uses 5-day lookback by default (adjustable by modifying iloc[-5])
        - All series must have sufficient history (at least 5 periods)
        - Regime is simplistic binary/ternary classification
        - Consider adding more sophisticated ML-based regime detection
        - Missing data will raise KeyError (ensure bundle is complete)

    Statistical considerations:
        - Simple threshold-based classification (no probabilistic inference)
        - Assumes linear relationship between indicators and regime
        - No consideration of magnitude (10% move = 0.1% move in scoring)
        - Consider using regime-switching models (HMM, MS-VAR) for robustness
    """
    from ..utils.helpers import percent_change

    # Calculate 5-day percentage changes
    dxy_change = percent_change(bundle.dxy_series.iloc[-1], bundle.dxy_series.iloc[-5])
    vix_change = percent_change(bundle.vix_series.iloc[-1], bundle.vix_series.iloc[-5])
    eem_change = percent_change(bundle.eem_series.iloc[-1], bundle.eem_series.iloc[-5])

    # Score each indicator
    score = 0

    # DXY: down = risk-on
    if dxy_change < 0:
        score += 1
    else:
        score -= 1

    # VIX: down = risk-on
    if vix_change < 0:
        score += 1
    else:
        score -= 1

    # EEM: up = risk-on
    if eem_change > 0:
        score += 1
    else:
        score -= 1

    # Classify regime
    if score >= 2:
        regime = "Risk-on"
    elif score <= -2:
        regime = "Risk-off"
    else:
        regime = "Neutral"

    return RiskGauge(
        dxy_change=dxy_change,
        vix_change=vix_change,
        eem_change=eem_change,
        regime=regime,
    )


__all__ = [
    "RiskGauge",
    "compute_risk_gauge",
]
