"""
Chilean AFP (Pension Fund) Flow Data Provider.

AFPs manage ~$200B USD and are major participants in the FX market.
Their international investment decisions significantly impact USD/CLP.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import httpx
import pandas as pd
from loguru import logger


class AFPFlowProvider:
    """
    Fetch and analyze AFP (Administradoras de Fondos de Pensiones) data.

    AFPs are Chile's pension fund administrators, managing mandatory
    retirement savings for millions of Chileans. They invest both
    domestically and internationally, making them major FX participants.

    Key insights:
    - Net outflows (buying foreign assets) = selling CLP = USD/CLP upward pressure
    - Net inflows (repatriating capital) = buying CLP = USD/CLP downward pressure
    - Monthly flows can exceed $1B USD

    Data sources:
    - Superintendencia de Pensiones (SP)
    - Banco Central de Chile

    Example:
        >>> provider = AFPFlowProvider()
        >>> flows = provider.get_net_international_flows(start_date)
        >>> print(f"Latest net flow: ${flows.iloc[-1]:.0f}M USD")
    """

    # SP API endpoints
    SP_BASE_URL = "https://www.spensiones.cl/apps/loadEstadisticas"
    SP_INVESTMENTS_URL = "https://www.spensiones.cl/portal/institucional/594/articles-13493_recurso_1.json"

    # BCCh series for AFP data
    BCCH_SERIES = {
        "afp_foreign_assets": "F091.AFP.INV.EXT.Z.USD",  # Foreign investments
        "afp_total_assets": "F091.AFP.ACT.TOT.Z.CLP",    # Total assets
        "afp_equity_foreign": "F091.AFP.RV.EXT.Z.USD",   # Foreign equity
        "afp_fixed_foreign": "F091.AFP.RF.EXT.Z.USD",    # Foreign fixed income
    }

    def __init__(self):
        """Initialize AFP flow provider."""
        self.client = httpx.Client(timeout=30.0)
        logger.info("AFPFlowProvider initialized")

    def get_net_international_flows(self, start_date: Optional[datetime] = None) -> pd.Series:
        """
        Fetch AFP net international investment flows.

        Positive values = net purchases of foreign assets (CLP weakness)
        Negative values = net sales/repatriation (CLP strength)

        Args:
            start_date: Start date for data (defaults to 2 years ago)

        Returns:
            Monthly net flows in millions USD
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 2)

        try:
            # Try to fetch from SP JSON endpoint
            flows = self._fetch_sp_flows()
            if not flows.empty:
                flows = flows[flows.index >= start_date]
                logger.info(f"Fetched {len(flows)} AFP flow observations from SP")
                return flows

        except Exception as e:
            logger.warning(f"Could not fetch AFP flows from SP: {e}")

        # Fallback: Calculate from investment positions
        return self._calculate_flows_from_positions(start_date)

    def get_foreign_investment_percentage(self, as_of_date: Optional[datetime] = None) -> float:
        """
        Get percentage of AFP assets invested internationally.

        Higher % = more exposed to FX movements
        Regulatory limit is ~80% for aggressive funds

        Args:
            as_of_date: Date for calculation (defaults to latest)

        Returns:
            Foreign investment percentage (0-100)
        """
        try:
            response = self.client.get(self.SP_INVESTMENTS_URL)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "resumen" in data:
                foreign_pct = data["resumen"].get("porcentaje_extranjero", 0)
                logger.info(f"AFP foreign investment: {foreign_pct:.1f}%")
                return foreign_pct

        except Exception as e:
            logger.error(f"Could not fetch AFP foreign percentage: {e}")

        return 0.0

    def get_fund_composition(self) -> Dict[str, Dict[str, float]]:
        """
        Get AFP fund composition by type (A, B, C, D, E).

        Fund types:
        - A: Most aggressive (up to 80% foreign equity)
        - B: Aggressive (up to 60% foreign equity)
        - C: Moderate (up to 40% foreign equity)
        - D: Conservative (up to 20% foreign equity)
        - E: Most conservative (up to 5% foreign equity)

        Returns:
            Dictionary with fund compositions
        """
        composition = {
            "A": {"foreign_equity": 80, "foreign_fixed": 20, "domestic": 0},
            "B": {"foreign_equity": 60, "foreign_fixed": 20, "domestic": 20},
            "C": {"foreign_equity": 40, "foreign_fixed": 20, "domestic": 40},
            "D": {"foreign_equity": 20, "foreign_fixed": 15, "domestic": 65},
            "E": {"foreign_equity": 5, "foreign_fixed": 10, "domestic": 85},
        }

        try:
            # Attempt to fetch actual compositions from SP
            response = self.client.get(
                f"{self.SP_BASE_URL}/getComposicionFondos",
                params={"_": int(datetime.now().timestamp() * 1000)}
            )
            response.raise_for_status()
            data = response.json()

            # Parse actual compositions if available
            if isinstance(data, list) and len(data) > 0:
                for fund_data in data:
                    fund_type = fund_data.get("tipo_fondo")
                    if fund_type in composition:
                        composition[fund_type] = {
                            "foreign_equity": fund_data.get("rv_extranjera", 0),
                            "foreign_fixed": fund_data.get("rf_extranjera", 0),
                            "domestic": fund_data.get("nacional", 0),
                        }

                logger.info("Updated AFP fund composition from SP data")

        except Exception as e:
            logger.warning(f"Using default fund compositions: {e}")

        return composition

    def analyze_flow_seasonality(self, flows: pd.Series) -> Dict[int, float]:
        """
        Analyze seasonal patterns in AFP flows.

        Key patterns:
        - December: Often repatriation for year-end liquidity
        - March/September: Rebalancing periods
        - July: Bonus payments increase contributions

        Args:
            flows: Historical flow series

        Returns:
            Average flow by month (1-12)
        """
        if flows.empty:
            return {}

        # Group by month and calculate average
        flows_df = pd.DataFrame({"flow": flows})
        flows_df["month"] = flows_df.index.month

        monthly_avg = flows_df.groupby("month")["flow"].mean().to_dict()

        # Identify seasonal patterns
        strongest_outflow_month = max(monthly_avg, key=monthly_avg.get)
        strongest_inflow_month = min(monthly_avg, key=monthly_avg.get)

        logger.info(f"AFP flow seasonality: "
                   f"Strongest outflows in month {strongest_outflow_month}, "
                   f"inflows in month {strongest_inflow_month}")

        return monthly_avg

    def _fetch_sp_flows(self) -> pd.Series:
        """
        Fetch flow data from Superintendencia de Pensiones.

        Returns:
            Series with monthly flows in millions USD
        """
        try:
            # Construct API request
            params = {
                "categoria": "inversiones_exterior",
                "periodo": "mensual",
                "_": int(datetime.now().timestamp() * 1000)
            }

            response = self.client.get(
                f"{self.SP_BASE_URL}/getInversionesExtranjeras",
                params=params
            )
            response.raise_for_status()

            data = response.json()

            if not isinstance(data, list) or len(data) == 0:
                logger.warning("No AFP flow data from SP API")
                return pd.Series(dtype=float)

            # Parse JSON into time series
            flows = {}
            for entry in data:
                try:
                    date_str = entry.get("fecha", "")
                    flow_value = entry.get("flujo_neto", 0)

                    # Parse date (format varies, try multiple)
                    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]:
                        try:
                            date = datetime.strptime(date_str, fmt)
                            flows[date] = float(flow_value)
                            break
                        except ValueError:
                            continue

                except (KeyError, ValueError) as e:
                    logger.debug(f"Skipping invalid AFP flow entry: {e}")

            if not flows:
                return pd.Series(dtype=float)

            series = pd.Series(flows, name="AFP Net International Flows")
            series = series.sort_index()

            # Log summary statistics
            if len(series) > 0:
                logger.info(f"AFP flows: Latest ${series.iloc[-1]:.0f}M USD, "
                           f"6m avg: ${series.tail(6).mean():.0f}M USD")

            return series

        except Exception as e:
            logger.error(f"Error fetching SP flows: {e}")
            return pd.Series(dtype=float)

    def _calculate_flows_from_positions(self, start_date: datetime) -> pd.Series:
        """
        Calculate flows from change in foreign investment positions.

        Flow = Change in position - FX valuation effect

        Args:
            start_date: Start date for calculation

        Returns:
            Estimated monthly flows in millions USD
        """
        try:
            # This would require access to detailed position data
            # For now, return empty series as this is a fallback
            logger.warning("Position-based flow calculation not implemented")
            return pd.Series(dtype=float, name="AFP Estimated Flows")

        except Exception as e:
            logger.error(f"Could not calculate flows from positions: {e}")
            return pd.Series(dtype=float)

    def get_regulatory_changes(self) -> List[Dict]:
        """
        Get recent regulatory changes affecting AFP investments.

        Important changes impact flow patterns:
        - Investment limit changes
        - New asset class permissions
        - Withdrawal regulations

        Returns:
            List of regulatory changes with dates and impacts
        """
        changes = [
            {
                "date": "2022-07-01",
                "description": "Alternative investment limit increased to 15%",
                "impact": "Potential for more international diversification"
            },
            {
                "date": "2021-12-01",
                "description": "Third pension withdrawal authorized",
                "impact": "Forced asset sales, including foreign holdings"
            },
            {
                "date": "2023-01-01",
                "description": "ESG requirements for investments",
                "impact": "May affect international allocation choices"
            }
        ]

        return changes

    def estimate_impact_on_usdclp(self, flow_millions_usd: float) -> float:
        """
        Estimate the impact of AFP flows on USD/CLP exchange rate.

        Rule of thumb: $100M flow = ~2-3 CLP move
        Actual impact depends on market conditions.

        Args:
            flow_millions_usd: Net flow in millions USD

        Returns:
            Estimated CLP impact (positive = depreciation)
        """
        # Base sensitivity: $100M = 2.5 CLP
        base_impact = 2.5
        flow_billions = flow_millions_usd / 1000

        # Non-linear impact (larger flows have proportionally bigger impact)
        if abs(flow_billions) > 0.5:
            impact_multiplier = 1.2
        else:
            impact_multiplier = 1.0

        estimated_impact = flow_billions * 10 * base_impact * impact_multiplier

        logger.info(f"Estimated USD/CLP impact from ${flow_millions_usd:.0f}M flow: "
                   f"{estimated_impact:+.1f} CLP")

        return estimated_impact

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, 'client'):
            self.client.close()