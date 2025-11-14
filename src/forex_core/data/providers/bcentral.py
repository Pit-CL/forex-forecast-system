"""
Banco Central de Chile Data Provider.

Provides access to Chilean economic indicators from the Central Bank of Chile's public API.
Includes: Trade Balance, Current Account, IMACEC, TPM history.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import httpx
import pandas as pd
from loguru import logger


class BancoCentralProvider:
    """
    Access Banco Central de Chile's public API for economic indicators.

    The Central Bank provides key economic data including trade balance,
    current account, IMACEC (monthly economic activity), and monetary policy rates.

    API Documentation: https://si3.bcentral.cl/Siete/ES/Siete/Cuadro

    Example:
        >>> provider = BancoCentralProvider()
        >>> trade_balance = provider.get_trade_balance(start_date, end_date)
        >>> imacec = provider.get_imacec(start_date, end_date)
    """

    BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

    # Key series IDs for Chilean economic indicators
    SERIES_IDS = {
        "trade_balance": "F032.BAL.COM.M.Z.Z.Z.CLP",  # Monthly trade balance
        "current_account": "F039.BP.CTA.CTE.Z.CLP",  # Quarterly current account
        "imacec": "F032.IMA.IND.A.M.Z",  # IMACEC index
        "imacec_yoy": "F032.IMA.VAR.ANU.M.Z",  # IMACEC YoY variation
        "tpm": "F022.TPM.TIN.D001.NO.Z.D",  # Monetary policy rate (TPM)
        "usd_exchange": "F073.TCO.PRE.Z.D",  # USD/CLP exchange rate
    }

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize BCCh provider.

        Args:
            username: BCCh API username (optional for public data)
            password: BCCh API password (optional for public data)
        """
        self.username = username or ""
        self.password = password or ""
        self.client = httpx.Client(timeout=30.0)
        logger.info("BancoCentralProvider initialized")

    def get_trade_balance(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Fetch Chilean trade balance (monthly).

        Trade balance = Exports - Imports
        Positive values indicate trade surplus (CLP supportive).
        Negative values indicate trade deficit (CLP negative).

        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            Series with trade balance in millions CLP, indexed by date
        """
        series_id = self.SERIES_IDS["trade_balance"]
        data = self._fetch_series(series_id, start_date, end_date, "Trade Balance")

        if not data.empty:
            logger.info(f"Trade balance: Latest {data.iloc[-1]:.0f}M CLP, "
                       f"3m avg: {data.tail(3).mean():.0f}M CLP")

        return data

    def get_current_account(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Fetch current account balance (quarterly).

        Current account includes trade balance + services + income + transfers.
        Key indicator of Chile's external position.

        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            Series with current account in millions CLP
        """
        series_id = self.SERIES_IDS["current_account"]
        return self._fetch_series(series_id, start_date, end_date, "Current Account")

    def get_imacec(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Fetch IMACEC (monthly economic activity index).

        IMACEC is Chile's leading economic activity indicator,
        published monthly (vs GDP quarterly). Critical for USD/CLP.

        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            Series with IMACEC index values
        """
        series_id = self.SERIES_IDS["imacec"]
        return self._fetch_series(series_id, start_date, end_date, "IMACEC")

    def get_imacec_yoy(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Fetch IMACEC year-over-year growth rate.

        YoY growth is the key metric watched by markets.
        Above 3% = strong growth (CLP positive)
        Below 0% = contraction (CLP negative)

        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            Series with IMACEC YoY growth rates (%)
        """
        series_id = self.SERIES_IDS["imacec_yoy"]
        data = self._fetch_series(series_id, start_date, end_date, "IMACEC YoY")

        if not data.empty:
            logger.info(f"IMACEC YoY: Latest {data.iloc[-1]:.1f}%, "
                       f"3m avg: {data.tail(3).mean():.1f}%")

        return data

    def get_tpm_history(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Fetch historical TPM (Tasa Política Monetaria) rates.

        Chile's monetary policy rate, set by BCCh.
        Higher TPM = CLP supportive (attracts capital)
        Lower TPM = CLP negative (capital outflows)

        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            Series with TPM rates (% annual)
        """
        series_id = self.SERIES_IDS["tpm"]
        return self._fetch_series(series_id, start_date, end_date, "TPM")

    def _fetch_series(self, series_id: str, start_date: datetime,
                     end_date: datetime, name: str) -> pd.Series:
        """
        Fetch time series from BCCh API.

        Args:
            series_id: BCCh series identifier
            start_date: Start date for data
            end_date: End date for data
            name: Human-readable name for logging

        Returns:
            Pandas Series with the requested data
        """
        params = {
            "user": self.username,
            "pass": self.password,
            "function": "GetSeries",
            "timeseries": series_id,
            "firstdate": start_date.strftime("%Y-%m-%d"),
            "lastdate": end_date.strftime("%Y-%m-%d"),
        }

        try:
            response = self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Check for errors in response
            error_elem = root.find(".//IngresarUsuarioResult")
            if error_elem is not None and error_elem.text == "RUT_INVALID":
                logger.warning(f"BCCh authentication failed for {name}, trying public access")
                params["user"] = ""
                params["pass"] = ""
                response = self.client.get(self.BASE_URL, params=params)
                root = ET.fromstring(response.content)

            # Extract data points from XML
            data_points = []
            for obs in root.findall(".//Obs"):
                date_elem = obs.find("indexDateString")
                value_elem = obs.find("value")

                if date_elem is not None and value_elem is not None:
                    try:
                        # Parse date (format: DD-MM-YYYY)
                        date_str = date_elem.text
                        date = datetime.strptime(date_str, "%d-%m-%Y")

                        # Parse value
                        value_str = value_elem.text
                        value = float(value_str.replace(",", ".")) if value_str else None

                        if value is not None:
                            data_points.append({"date": date, "value": value})
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Skipping invalid data point in {name}: {e}")

            if not data_points:
                logger.warning(f"No data points found for {name} series {series_id}")
                return pd.Series(dtype=float, name=name)

            # Convert to Series
            df = pd.DataFrame(data_points)
            series = pd.Series(
                df["value"].values,
                index=pd.DatetimeIndex(df["date"]),
                name=name
            )

            # Remove duplicates, keeping last
            series = series[~series.index.duplicated(keep="last")]
            series = series.sort_index()

            logger.info(f"Fetched {len(series)} points for {name} from BCCh "
                       f"({series.index[0].strftime('%Y-%m-%d')} to "
                       f"{series.index[-1].strftime('%Y-%m-%d')})")

            return series

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {name} from BCCh: {e}")
            return pd.Series(dtype=float, name=name)
        except ET.ParseError as e:
            logger.error(f"XML parse error for {name}: {e}")
            return pd.Series(dtype=float, name=name)
        except Exception as e:
            logger.error(f"Unexpected error fetching {name} from BCCh: {e}")
            return pd.Series(dtype=float, name=name)

    def get_all_indicators(self, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> dict:
        """
        Fetch all available Chilean indicators in one call.

        Args:
            start_date: Start date (defaults to 2 years ago)
            end_date: End date (defaults to today)

        Returns:
            Dictionary with all indicator series
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)
        if end_date is None:
            end_date = datetime.now()

        indicators = {}

        # Fetch each indicator
        for key, desc in [
            ("trade_balance", "Trade Balance"),
            ("imacec_yoy", "IMACEC YoY"),
            ("tpm", "TPM History"),
        ]:
            try:
                if key == "trade_balance":
                    data = self.get_trade_balance(start_date, end_date)
                elif key == "imacec_yoy":
                    data = self.get_imacec_yoy(start_date, end_date)
                elif key == "tpm":
                    data = self.get_tpm_history(start_date, end_date)

                if not data.empty:
                    indicators[key] = data
                    logger.info(f"Loaded {desc}: {len(data)} observations")
            except Exception as e:
                logger.warning(f"Failed to load {desc}: {e}")

        logger.info(f"Loaded {len(indicators)} Chilean indicators from BCCh")
        return indicators

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, 'client'):
            self.client.close()