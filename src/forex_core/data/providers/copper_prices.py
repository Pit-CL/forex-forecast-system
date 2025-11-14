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

Additional Data:
- LME inventory levels (via web scraping or API)
- COMEX warehouse stocks

This provider fetches copper price data and computes features for forecasting:
- Raw price series (normalized)
- Returns (1d, 5d, 20d log returns)
- Volatility (20d, 60d rolling std, annualized)
- Trend indicators (SMA 20/50, trend signal)
- Momentum (RSI 14)
- Inventory levels (LME, COMEX)
- Inventory change rates
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
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
        self.http_client = httpx.Client(timeout=30.0)

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
        trend_array = np.where(
            features["copper_sma_20"] > features["copper_sma_50"],
            1.0,
            np.where(features["copper_sma_20"] < features["copper_sma_50"], -1.0, 0.0)
        )
        features["copper_trend_signal"] = pd.Series(trend_array, index=series.index, name="copper_trend_signal")

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

    def get_lme_inventory(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Fetch LME copper warehouse inventory levels.

        Lower inventory = supply tightness = bullish for copper = bullish for CLP
        Higher inventory = supply excess = bearish for copper = bearish for CLP

        Note: This uses FRED data as LME direct access requires subscription.
        Series: WMLMEBCMTN - LME Copper Warehouse Stocks, metric tons

        Args:
            start_date: Start date for data (defaults to 2 years ago)

        Returns:
            Series with LME inventory in metric tons
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        if not self.fred_client:
            logger.warning("Cannot fetch LME inventory: No FRED API key configured")
            return pd.Series(dtype=float, name="LME Copper Inventory")

        try:
            # FRED series for LME copper stocks
            df = self.fred_client.get_series(
                "WMLMEBCMTN",
                observation_start=start_date.date()
            )

            if df.empty:
                logger.warning("No LME inventory data available from FRED")
                return pd.Series(dtype=float, name="LME Copper Inventory")

            # Convert to Series
            series = pd.Series(
                df.iloc[:, 0].values,
                index=df.index,
                name="LME Copper Inventory"
            )

            # Log current levels
            latest = series.iloc[-1]
            avg_90d = series.tail(90).mean()
            pct_change = ((latest - avg_90d) / avg_90d) * 100

            logger.info(f"LME Copper Inventory: {latest:,.0f} MT, "
                       f"90d avg: {avg_90d:,.0f} MT ({pct_change:+.1f}%)")

            return series

        except Exception as e:
            logger.error(f"Failed to fetch LME inventory: {e}")
            return pd.Series(dtype=float, name="LME Copper Inventory")

    def compute_inventory_features(self, inventory: pd.Series) -> Dict[str, pd.Series]:
        """
        Compute inventory-based features for forecasting.

        Features:
        - Inventory levels (normalized)
        - Inventory change rate (daily, weekly)
        - Days of consumption (inventory/daily demand estimate)
        - Inventory z-score (deviation from historical mean)

        Args:
            inventory: LME inventory time series

        Returns:
            Dictionary of inventory features
        """
        if inventory.empty:
            return {}

        features = {}

        try:
            # Fill missing values (inventory reported weekly)
            inventory = inventory.ffill()

            # Inventory change rates
            features['inventory_change_1d'] = inventory.diff()
            features['inventory_change_5d'] = inventory.diff(5)
            features['inventory_change_pct_5d'] = inventory.pct_change(5) * 100

            # Rolling statistics
            features['inventory_ma_20d'] = inventory.rolling(20).mean()
            features['inventory_ma_60d'] = inventory.rolling(60).mean()

            # Z-score (standardized inventory level)
            rolling_mean = inventory.rolling(252).mean()  # 1-year rolling
            rolling_std = inventory.rolling(252).std()
            features['inventory_zscore'] = (inventory - rolling_mean) / rolling_std

            # Inventory trend signal
            features['inventory_trend'] = np.where(
                features['inventory_ma_20d'] > features['inventory_ma_60d'],
                1,  # Rising inventory (bearish)
                -1  # Falling inventory (bullish)
            )

            # Days of consumption (assuming ~30k MT daily global consumption)
            daily_consumption_estimate = 30000
            features['days_of_supply'] = inventory / daily_consumption_estimate

            # Critical level indicators
            # Historical low: ~100k MT, Historical high: ~700k MT
            features['inventory_critical_low'] = (inventory < 150000).astype(int)
            features['inventory_critical_high'] = (inventory > 600000).astype(int)

            logger.info(f"Computed {len(features)} inventory features")

        except Exception as e:
            logger.error(f"Failed to compute inventory features: {e}")

        return features

    def get_comex_inventory(self) -> Optional[float]:
        """
        Fetch latest COMEX copper warehouse stocks.

        COMEX is the US futures exchange, complementary to LME.

        Returns:
            Latest COMEX inventory in short tons, or None if unavailable
        """
        try:
            # COMEX publishes daily warehouse stocks report
            # This would require CME Group API access or web scraping
            logger.warning("COMEX inventory fetching not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch COMEX inventory: {e}")
            return None

    def analyze_inventory_price_relationship(
        self,
        prices: pd.Series,
        inventory: pd.Series,
        window: int = 90
    ) -> pd.Series:
        """
        Analyze relationship between inventory and price.

        Generally inverse relationship:
        - Falling inventory + rising price = strong bull market
        - Rising inventory + falling price = strong bear market
        - Divergence can signal turning points

        Args:
            prices: Copper price series
            inventory: Inventory series
            window: Rolling correlation window (days)

        Returns:
            Rolling correlation series
        """
        if prices.empty or inventory.empty:
            return pd.Series(dtype=float)

        try:
            # Align series to common dates
            aligned = pd.DataFrame({
                'price': prices,
                'inventory': inventory
            }).dropna()

            if len(aligned) < window:
                logger.warning(f"Insufficient data for {window}-day correlation")
                return pd.Series(dtype=float)

            # Calculate rolling correlation
            correlation = aligned['price'].rolling(window).corr(aligned['inventory'])
            correlation.name = f"Price-Inventory Correlation ({window}d)"

            # Log current relationship
            latest_corr = correlation.iloc[-1]
            logger.info(f"Price-Inventory correlation ({window}d): {latest_corr:.3f} "
                       f"({'Inverse' if latest_corr < -0.3 else 'Normal' if latest_corr < 0.3 else 'Positive'})")

            return correlation

        except Exception as e:
            logger.error(f"Failed to analyze inventory-price relationship: {e}")
            return pd.Series(dtype=float)


__all__ = ["CopperPricesClient"]
