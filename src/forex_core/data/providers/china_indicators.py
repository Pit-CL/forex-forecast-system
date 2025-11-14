"""
China Economic Indicators Provider.

Focuses on Manufacturing PMI as a proxy for copper demand.
China consumes ~50% of global copper production.
"""

from datetime import datetime, timedelta
from typing import Optional

import httpx
import pandas as pd
from loguru import logger


class ChinaPMIProvider:
    """
    Fetch China Manufacturing PMI data.

    PMI is a leading indicator of economic health:
    - PMI > 50: Economic expansion (higher copper demand, CLP positive)
    - PMI = 50: No change
    - PMI < 50: Economic contraction (lower copper demand, CLP negative)

    China's PMI directly impacts copper prices as China is the largest consumer.

    Example:
        >>> provider = ChinaPMIProvider(fred_api_key="your_key")
        >>> pmi = provider.get_manufacturing_pmi(start_date)
        >>> print(f"Latest PMI: {pmi.iloc[-1]:.1f}")
    """

    # FRED series for China indicators
    FRED_SERIES = {
        "manufacturing_pmi": "MPMICN",  # China Manufacturing PMI
        "caixin_pmi": "CHNMANPMICAX",  # Caixin Manufacturing PMI (private sector)
        "industrial_production": "CHNIPIMON",  # Industrial Production YoY
        "fixed_investment": "CHINVFAYOY",  # Fixed Asset Investment YoY
    }

    FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, fred_api_key: Optional[str] = None):
        """
        Initialize China PMI provider.

        Args:
            fred_api_key: FRED API key for accessing data
        """
        self.fred_api_key = fred_api_key
        self.client = httpx.Client(timeout=30.0)

        if not fred_api_key:
            logger.warning("No FRED API key provided. Some data may be unavailable.")

    def get_manufacturing_pmi(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Fetch China Manufacturing PMI from FRED.

        This is the official NBS (National Bureau of Statistics) PMI.
        Published monthly on the last day of each month.

        Key levels:
        - Above 53: Strong expansion
        - 50-53: Moderate expansion
        - 48-50: Mild contraction
        - Below 48: Sharp contraction

        Args:
            start_date: Start date for data (defaults to 2 years ago)

        Returns:
            Monthly PMI values as Series
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        series = self._fetch_fred_series(
            self.FRED_SERIES["manufacturing_pmi"],
            start_date,
            "Manufacturing PMI"
        )

        if not series.empty:
            latest = series.iloc[-1]
            avg_3m = series.tail(3).mean()
            logger.info(f"China Manufacturing PMI: Latest {latest:.1f}, "
                       f"3m avg: {avg_3m:.1f} "
                       f"({'Expansion' if latest > 50 else 'Contraction'})")

        return series

    def get_caixin_pmi(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Fetch Caixin Manufacturing PMI.

        Caixin PMI focuses on smaller, private companies.
        Often diverges from official PMI, providing additional insight.

        Args:
            start_date: Start date for data

        Returns:
            Monthly Caixin PMI values
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        return self._fetch_fred_series(
            self.FRED_SERIES["caixin_pmi"],
            start_date,
            "Caixin PMI"
        )

    def get_industrial_production(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Fetch China Industrial Production YoY growth.

        Industrial production correlates strongly with copper consumption.
        Higher growth = more copper demand.

        Args:
            start_date: Start date for data

        Returns:
            Monthly industrial production YoY growth (%)
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        return self._fetch_fred_series(
            self.FRED_SERIES["industrial_production"],
            start_date,
            "Industrial Production YoY"
        )

    def get_composite_copper_demand_index(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Create composite index of China copper demand indicators.

        Combines PMI, Caixin PMI, and industrial production into
        a single copper demand score.

        Args:
            start_date: Start date for data

        Returns:
            Composite demand index (0-100 scale)
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        indicators = {}

        # Fetch all indicators
        pmi = self.get_manufacturing_pmi(start_date)
        if not pmi.empty:
            indicators["pmi"] = pmi

        caixin = self.get_caixin_pmi(start_date)
        if not caixin.empty:
            indicators["caixin"] = caixin

        ip = self.get_industrial_production(start_date)
        if not ip.empty:
            # Normalize IP growth to 0-100 scale
            # Assume -5% to +15% range maps to 0-100
            ip_normalized = ((ip + 5) / 20) * 100
            ip_normalized = ip_normalized.clip(0, 100)
            indicators["ip"] = ip_normalized

        if not indicators:
            logger.warning("No China indicators available for composite index")
            return pd.Series(dtype=float, name="China Copper Demand Index")

        # Combine indicators with weights
        weights = {
            "pmi": 0.4,      # Official PMI gets highest weight
            "caixin": 0.3,   # Caixin PMI
            "ip": 0.3,       # Industrial production
        }

        # Align all series to common dates
        df = pd.DataFrame(indicators)
        df = df.dropna()

        if df.empty:
            return pd.Series(dtype=float, name="China Copper Demand Index")

        # Calculate weighted average
        composite = pd.Series(0.0, index=df.index, name="China Copper Demand Index")
        total_weight = 0.0

        for col in df.columns:
            if col in weights:
                composite += df[col] * weights[col]
                total_weight += weights[col]

        if total_weight > 0:
            composite = composite / total_weight

        logger.info(f"Composite China copper demand index: "
                   f"Latest {composite.iloc[-1]:.1f}, "
                   f"3m avg: {composite.tail(3).mean():.1f}")

        return composite

    def _fetch_fred_series(self, series_id: str, start_date: datetime,
                          name: str) -> pd.Series:
        """
        Fetch time series from FRED API.

        Args:
            series_id: FRED series identifier
            start_date: Start date for data
            name: Human-readable name for logging

        Returns:
            Series with the requested data
        """
        if not self.fred_api_key:
            logger.warning(f"Cannot fetch {name}: No FRED API key configured")
            return pd.Series(dtype=float, name=name)

        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "observation_start": start_date.strftime("%Y-%m-%d"),
        }

        try:
            response = self.client.get(self.FRED_BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()
            observations = data.get("observations", [])

            if not observations:
                logger.warning(f"No observations found for {name} (series: {series_id})")
                return pd.Series(dtype=float, name=name)

            # Parse into Series
            dates = []
            values = []

            for obs in observations:
                if obs["value"] != "." and obs["value"]:  # Skip missing values
                    try:
                        dates.append(pd.to_datetime(obs["date"]))
                        values.append(float(obs["value"]))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid observation in {name}: {e}")

            if not dates:
                logger.warning(f"No valid data points for {name}")
                return pd.Series(dtype=float, name=name)

            series = pd.Series(values, index=dates, name=name)
            series = series.sort_index()

            logger.info(f"Fetched {len(series)} {name} observations from FRED")

            return series

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {name} from FRED: {e}")
            return pd.Series(dtype=float, name=name)
        except Exception as e:
            logger.error(f"Failed to fetch {name} from FRED: {e}")
            return pd.Series(dtype=float, name=name)

    def analyze_pmi_momentum(self, pmi_series: pd.Series, window: int = 3) -> pd.Series:
        """
        Analyze PMI momentum (rate of change).

        Momentum can be more important than absolute level.
        Rising PMI from 48 to 49 is bullish even though still below 50.

        Args:
            pmi_series: PMI time series
            window: Number of months for momentum calculation

        Returns:
            Series with PMI momentum values
        """
        if pmi_series.empty:
            return pd.Series(dtype=float, name="PMI Momentum")

        # Calculate month-over-month change
        momentum = pmi_series.diff(window)
        momentum.name = "PMI Momentum"

        # Log significant changes
        latest_momentum = momentum.iloc[-1] if not momentum.empty else 0
        if abs(latest_momentum) > 2:
            logger.info(f"Significant PMI momentum: {latest_momentum:+.1f} points over {window} months")

        return momentum

    def get_expansion_probability(self, pmi_series: pd.Series) -> float:
        """
        Calculate probability of economic expansion based on PMI.

        Uses logistic function centered at 50.

        Args:
            pmi_series: PMI time series

        Returns:
            Probability of expansion (0-1)
        """
        if pmi_series.empty:
            return 0.5

        latest_pmi = pmi_series.iloc[-1]

        # Logistic function: 1 / (1 + exp(-k*(x-50)))
        # k controls steepness, using 0.2 for smooth transition
        import numpy as np
        k = 0.2
        probability = 1 / (1 + np.exp(-k * (latest_pmi - 50)))

        return probability

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, 'client'):
            self.client.close()