"""
Technical analysis indicators for forex pairs.

This module provides functions to compute technical indicators commonly used
in currency trading analysis, including moving averages, RSI, MACD, Bollinger
Bands, and volatility metrics.

All calculations follow industry-standard methodologies:
- RSI: Uses Wilder's smoothing (SMA-based)
- MACD: Exponential moving average convergence/divergence
- Bollinger Bands: 20-period MA +/- 2 standard deviations
- Volatility: Annualized log-return standard deviation

Functions:
    compute_technicals: Compute full suite of technical indicators
    calculate_rsi: Calculate Relative Strength Index
    calculate_macd: Calculate MACD line and signal line
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


def compute_technicals(series: pd.Series) -> Dict[str, float | pd.Series | Dict]:
    """
    Compute comprehensive technical analysis indicators for a price series.

    This function calculates moving averages, Bollinger Bands, RSI, MACD,
    historical volatility, support/resistance levels, and day-of-week seasonality.

    Args:
        series: Time series of prices (typically daily close prices).
                Index must be DatetimeIndex.

    Returns:
        Dictionary containing:
            - latest_close: Most recent closing price
            - ma_5, ma_20, ma_50: Moving averages (5, 20, 50 periods)
            - bb_upper, bb_lower: Bollinger Band levels
            - rsi_14: Relative Strength Index (14 periods)
            - macd, macd_signal: MACD line and signal line
            - hist_vol_30: 30-day historical volatility (annualized)
            - support, resistance: Support/resistance levels (10-period min/max)
            - seasonality: Average returns by day of week
            - frame: Full DataFrame with all computed indicators

    Example:
        >>> import pandas as pd
        >>> prices = pd.Series([950, 955, 948, 952, 960],
        ...                    index=pd.date_range('2025-01-01', periods=5))
        >>> technicals = compute_technicals(prices)
        >>> print(f"RSI: {technicals['rsi_14']:.2f}")
        >>> print(f"Support: {technicals['support']:.2f}")

    Notes:
        - Requires sufficient data for all indicators (minimum 50 periods recommended)
        - NaN values will appear in early periods for indicators with lookback windows
        - Volatility is annualized assuming 252 trading days
        - Support/resistance use simple 10-period rolling min/max
    """
    frame = series.to_frame(name="close").copy()

    # Moving averages
    frame["ma_5"] = frame["close"].rolling(5).mean()
    frame["ma_20"] = frame["close"].rolling(20).mean()
    frame["ma_50"] = frame["close"].rolling(50).mean()

    # Returns (for volatility and seasonality)
    frame["returns"] = frame["close"].pct_change()
    frame["log_returns"] = np.log(frame["close"]).diff()

    # Bollinger Bands (20-period, 2 std dev)
    bollinger_mid = frame["ma_20"]
    bollinger_std = frame["close"].rolling(20).std()
    frame["bb_upper"] = bollinger_mid + 2 * bollinger_std
    frame["bb_lower"] = bollinger_mid - 2 * bollinger_std

    # RSI (14-period)
    frame["rsi_14"] = calculate_rsi(frame["close"], period=14)

    # MACD (12/26/9)
    macd_line, signal_line = calculate_macd(frame["close"])
    frame["macd"] = macd_line
    frame["macd_signal"] = signal_line

    # Historical volatility (30-day, annualized)
    frame["hist_vol_30"] = frame["log_returns"].rolling(30).std() * np.sqrt(252)

    # Support and resistance (10-period rolling min/max)
    support = frame["close"].rolling(10).min().iloc[-1]
    resistance = frame["close"].rolling(10).max().iloc[-1]

    # Day-of-week seasonality
    seasonality = frame["returns"].dropna()
    seasonality = (
        seasonality.groupby(seasonality.index.dayofweek)
        .mean()
        .rename(index=lambda x: ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][x])
    )

    # Extract latest values
    latest = frame.iloc[-1]
    payload = {
        "latest_close": float(latest["close"]),
        "ma_5": float(latest["ma_5"]),
        "ma_20": float(latest["ma_20"]),
        "ma_50": float(latest["ma_50"]),
        "bb_upper": float(latest["bb_upper"]),
        "bb_lower": float(latest["bb_lower"]),
        "rsi_14": float(latest["rsi_14"]),
        "macd": float(latest["macd"]),
        "macd_signal": float(latest["macd_signal"]),
        "hist_vol_30": float(latest["hist_vol_30"]),
        "support": float(support),
        "resistance": float(resistance),
        "seasonality": seasonality.to_dict(),
        "frame": frame,
    }
    return payload


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) using Wilder's smoothing method.

    RSI measures the magnitude of recent price changes to evaluate overbought
    or oversold conditions. Values range from 0 to 100:
    - RSI > 70: Potentially overbought
    - RSI < 30: Potentially oversold
    - RSI = 50: Neutral momentum

    Formula:
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period

    Args:
        series: Price series (typically close prices).
        period: Lookback period for averaging (default 14).

    Returns:
        Series of RSI values (same index as input).

    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105, 104, 106])
        >>> rsi = calculate_rsi(prices, period=3)
        >>> print(rsi.iloc[-1])  # Latest RSI value

    Notes:
        - This implementation uses simple moving average (SMA) for gains/losses
        - Traditional RSI uses Wilder's smoothing (exponential moving average)
        - First `period` values will be NaN
        - Avoid division by zero: if avg_loss = 0, RSI = 100
    """
    delta = series.diff()

    # Separate gains and losses
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    # Calculate rolling averages
    roll_up = pd.Series(gain, index=series.index).rolling(period).mean()
    roll_down = pd.Series(loss, index=series.index).rolling(period).mean()

    # Compute RS and RSI
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence/Divergence) indicator.

    MACD is a trend-following momentum indicator that shows the relationship
    between two exponential moving averages (EMAs) of prices.

    Components:
        - MACD Line: EMA(fast) - EMA(slow)
        - Signal Line: EMA(MACD Line, signal periods)
        - Histogram: MACD Line - Signal Line (not returned, but easily derived)

    Trading Signals:
        - Bullish: MACD crosses above signal line
        - Bearish: MACD crosses below signal line
        - Divergence: Price makes new high/low but MACD doesn't (reversal signal)

    Args:
        series: Price series (typically close prices).
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        Tuple of (macd_line, signal_line) as pandas Series.

    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        >>> macd, signal = calculate_macd(prices)
        >>> histogram = macd - signal
        >>> if macd.iloc[-1] > signal.iloc[-1]:
        ...     print("Bullish crossover")

    Notes:
        - Uses exponential moving average with `adjust=False` (standard method)
        - MACD is typically displayed as histogram (MACD - Signal)
        - Default parameters (12, 26, 9) are industry standard
        - First ~34 periods will have NaN values (slow + signal)
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


__all__ = [
    "compute_technicals",
    "calculate_rsi",
    "calculate_macd",
]
