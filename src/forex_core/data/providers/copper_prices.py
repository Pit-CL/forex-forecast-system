"""
Copper prices data provider with dual-source fallback strategy.

Primary Source: Yahoo Finance (HG=F - COMEX Copper Futures)
- Real-time daily updates
- 10+ years historical data
- USD per pound

Backup Source: FRED API (PCOPPUSDM - Global Price of Copper)
- Monthly updates (slower but very reliable)
- USD per metric ton
- Requires FRED_API_KEY

This provider fetches copper price data and computes features for forecasting:
- Raw price series (normalized)
- Returns (1d, 5d, 20d log returns)
- Volatility (20d, 60d rolling std, annualized)
- Trend indicators (SMA 20/50, trend signal)
- Momentum (RSI 14)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import Indicator
from .yahoo import YahooClient
from .fred import FredClient


class CopperPricesClient:
    """
    Copper price data provider with automatic fallback.

    Uses Yahoo Finance as primary source (HG=F) and FRED API as backup.
    Computes technical indicators and features for forecasting pipeline.

    Attributes:
        settings: Application settings.
        yahoo_client: Yahoo Finance client for HG=F data.
        fred_client: Optional FRED client for PCOPPUSDM backup.

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> client = CopperPricesClient(settings)
        >>> series = client.fetch_series(years=5)
        >>> print(f"Fetched {len(series)} copper price points")
        >>> features = client.compute_features(series)
        >>> print(features.keys())
        dict_keys(['copper_returns_1d', 'copper_volatility_20d', ...])
    """

    # Conversion constant: 1 metric ton = 2204.62 pounds
    LBS_PER_TON = 2204.62

    def __init__(self, settings: Settings) -> None:
        """
        Initialize copper prices client with dual sources.

        Args:
            settings: Application settings with optional FRED_API_KEY.

        Example:
            >>> settings = get_settings()
            >>> client = CopperPricesClient(settings)
        """
        self.settings = settings
        self.yahoo_client = YahooClient(settings)

        # Optional FRED backup
        self.fred_client: Optional[FredClient] = None
        if settings.fred_api_key:
            try:
                self.fred_client = FredClient(settings)
                logger.info("FRED backup source available for copper prices")
            except Exception as e:
                logger.warning(f"FRED client init failed, Yahoo-only mode: {e}")

    def fetch_series(
        self,
        *,
        years: int = 5,
        force_backup: bool = False,
    ) -> pd.Series:
        """
        Fetch historical copper price series with automatic fallback.

        Primary: Yahoo Finance HG=F (COMEX Copper Futures, USD/lb)
        Backup: FRED PCOPPUSDM (Global Price, USD/metric ton, converted to USD/lb)

        Args:
            years: Number of years of historical data to fetch. Default: 5.
            force_backup: Force use of FRED backup even if Yahoo works. Default: False.

        Returns:
            pandas Series with daily copper prices in USD per pound.
            Index is datetime, values are float prices.

        Raises:
            RuntimeError: If both primary and backup sources fail.

        Example:
            >>> series = client.fetch_series(years=10)
            >>> print(f"Price range: ${series.min():.2f} - ${series.max():.2f}")
            Price range: $2.15 - $5.04
            >>> print(f"Latest: ${series.iloc[-1]:.2f} on {series.index[-1]}")
            Latest: $3.82 on 2025-11-12 00:00:00
        """
        # Try primary source (Yahoo Finance)
        if not force_backup:
            try:
                logger.info(f"Fetching copper prices from Yahoo Finance (HG=F, {years}y)")
                series = self.yahoo_client.fetch_series(
                    "HG=F",
                    range_window=f"{years}y"
                )
                series.name = "copper_usd_lb"
                logger.info(
                    f"Successfully fetched {len(series)} copper price points from Yahoo "
                    f"(range: ${series.min():.2f}-${series.max():.2f})"
                )
                return series
            except Exception as e:
                logger.warning(f"Yahoo Finance copper fetch failed: {e}")

        # Fallback to FRED
        if self.fred_client:
            try:
                logger.info("Using FRED backup for copper prices (PCOPPUSDM)")
                df = self.fred_client.get_series("PCOPPUSDM")

                # Convert USD/metric ton to USD/lb for consistency
                series = df["PCOPPUSDM"] / self.LBS_PER_TON
                series.name = "copper_usd_lb"

                logger.info(
                    f"Successfully fetched {len(series)} copper price points from FRED "
                    f"(range: ${series.min():.2f}-${series.max():.2f})"
                )
                return series
            except Exception as e:
                logger.error(f"FRED backup also failed: {e}")
                raise RuntimeError(
                    "Both Yahoo Finance and FRED copper sources failed. "
                    "Cannot continue without copper data."
                )
        else:
            raise RuntimeError(
                "Yahoo Finance failed and FRED backup not available (missing API key). "
                "Set FRED_API_KEY environment variable for fallback capability."
            )

    def get_latest_indicator(self, source_id: int) -> Indicator:
        """
        Get current copper spot price as an Indicator object.

        Args:
            source_id: Source registry ID for attribution.

        Returns:
            Indicator with latest copper price in USD/lb.

        Raises:
            RuntimeError: If fetching latest price fails.

        Example:
            >>> indicator = client.get_latest_indicator(source_id=42)
            >>> print(f"{indicator.name}: ${indicator.value:.2f} {indicator.unit}")
            Precio del cobre: $3.82 USD/lb
        """
        try:
            # Fetch just last 30 days for speed
            series = self.fetch_series(years=1)
            latest_value = float(series.iloc[-1])
            latest_date = series.index[-1].to_pydatetime()

            return Indicator(
                name="Precio del cobre",
                value=latest_value,
                unit="USD/lb",
                timestamp=latest_date,
                source_id=source_id,
            )
        except Exception as e:
            logger.error(f"Failed to get latest copper indicator: {e}")
            raise RuntimeError(f"Could not fetch latest copper price: {e}")

    def compute_features(self, series: pd.Series) -> Dict[str, pd.Series]:
        """
        Compute copper-derived features for forecasting model.

        Calculates technical indicators and statistical features:
        - Returns: 1d, 5d, 20d log returns
        - Volatility: 20d, 60d rolling std (annualized)
        - Trend: SMA 20/50, trend signal
        - Momentum: RSI 14

        Args:
            series: Raw copper price series (USD/lb).

        Returns:
            Dictionary mapping feature names to pandas Series.
            All series have same index as input, with NaN for initial periods.

        Example:
            >>> series = client.fetch_series(years=5)
            >>> features = client.compute_features(series)
            >>> print(features['copper_volatility_20d'].tail(3))
            2025-11-10    0.234
            2025-11-11    0.241
            2025-11-12    0.238
            Name: copper_volatility_20d, dtype: float64
        """
        features: Dict[str, pd.Series] = {}

        # 1. LOG RETURNS (various horizons)
        features["copper_returns_1d"] = np.log(series / series.shift(1))
        features["copper_returns_5d"] = np.log(series / series.shift(5))
        features["copper_returns_20d"] = np.log(series / series.shift(20))

        # 2. VOLATILITY (annualized rolling std)
        # Formula: std(log_returns) * sqrt(252) for annualization
        returns_1d = features["copper_returns_1d"]
        features["copper_volatility_20d"] = (
            returns_1d.rolling(window=20).std() * np.sqrt(252)
        )
        features["copper_volatility_60d"] = (
            returns_1d.rolling(window=60).std() * np.sqrt(252)
        )

        # 3. TREND INDICATORS (Simple Moving Averages)
        features["copper_sma_20"] = series.rolling(window=20).mean()
        features["copper_sma_50"] = series.rolling(window=50).mean()

        # Trend signal: 1 if SMA20 > SMA50 (uptrend), -1 if downtrend, 0 if equal
        features["copper_trend_signal"] = np.where(
            features["copper_sma_20"] > features["copper_sma_50"],
            1.0,
            np.where(features["copper_sma_20"] < features["copper_sma_50"], -1.0, 0.0)
        )

        # 4. MOMENTUM - RSI (Relative Strength Index, 14 periods)
        features["copper_rsi_14"] = self._calculate_rsi(series, period=14)

        # 5. NORMALIZED PRICE (for model input)
        # Z-score normalization over 1-year rolling window
        features["copper_price_normalized"] = (
            (series - series.rolling(window=252).mean()) /
            series.rolling(window=252).std()
        )

        logger.debug(
            f"Computed {len(features)} copper features "
            f"(mean volatility_20d: {features['copper_volatility_20d'].mean():.3f})"
        )

        return features

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI is a momentum oscillator measuring speed/change of price movements.
        Values range from 0 to 100:
        - RSI > 70: Overbought (potential reversal down)
        - RSI < 30: Oversold (potential reversal up)

        Args:
            series: Price series.
            period: RSI period (typically 14). Default: 14.

        Returns:
            RSI series with same index as input.

        Example:
            >>> rsi = client._calculate_rsi(copper_series, period=14)
            >>> print(f"Current RSI: {rsi.iloc[-1]:.1f}")
            Current RSI: 58.3
        """
        # Calculate price changes
        delta = series.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Calculate average gain and loss using exponential moving average
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Relative strength
        rs = avg_gain / avg_loss

        # RSI formula
        rsi = 100.0 - (100.0 / (1.0 + rs))

        rsi.name = f"copper_rsi_{period}"
        return rsi

    def compute_correlation_with_usdclp(
        self,
        copper_series: pd.Series,
        usdclp_series: pd.Series,
        window: int = 90,
    ) -> pd.Series:
        """
        Compute rolling correlation between copper and USD/CLP.

        This helps detect regime changes where copper-peso relationship shifts.

        Args:
            copper_series: Copper price series (USD/lb).
            usdclp_series: USD/CLP exchange rate series.
            window: Rolling window in days. Default: 90.

        Returns:
            Series of rolling correlation coefficients (-1 to 1).

        Example:
            >>> correlation = client.compute_correlation_with_usdclp(
            ...     copper_series, usdclp_series, window=90
            ... )
            >>> print(f"Current 90-day correlation: {correlation.iloc[-1]:.3f}")
            Current 90-day correlation: -0.687
            >>> # Negative correlation is expected: higher copper -> stronger CLP -> lower USD/CLP
        """
        # Align series by index
        aligned = pd.DataFrame({
            "copper": copper_series,
            "usdclp": usdclp_series,
        }).dropna()

        # Rolling correlation
        correlation = aligned["copper"].rolling(window=window).corr(aligned["usdclp"])
        correlation.name = f"copper_usdclp_correlation_{window}d"

        logger.debug(
            f"Copper-USDCLP correlation (mean {window}d): {correlation.mean():.3f}"
        )

        return correlation


__all__ = ["CopperPricesClient"]
