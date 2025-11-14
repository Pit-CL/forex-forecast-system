"""
Data loader orchestrator.

Coordinates all data providers to load a complete dataset for forecasting.
Handles data fetching, caching, error recovery, and source tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import pandas as pd
from loguru import logger

from forex_core.config import Settings, get_settings
from forex_core.data.models import Indicator, MacroEvent, NewsHeadline
from forex_core.data.providers import (
    AlphaVantageClient,
    BackupMacroCalendarClient,
    CopperPricesClient,
    FederalReserveClient,
    FredClient,
    MacroCalendarClient,
    MindicadorClient,
    XeClient,
    YahooClient,
)
from forex_core.data.providers.bcentral import BancoCentralProvider
from forex_core.data.providers.china_indicators import ChinaPMIProvider
from forex_core.data.providers.afp_flows import AFPFlowProvider
from forex_core.data.registry import SourceRegistry
from forex_core.data.warehouse import Warehouse


@dataclass
class DataBundle:
    """
    Complete data package for forex forecasting.

    Attributes:
        usdclp_series: Historical USD/CLP daily exchange rate.
        copper_series: Historical copper price (LME).
        tpm_series: Chilean monetary policy rate history.
        inflation_series: Chilean CPI history.
        indicators: Current market indicators (spot rates, indices, etc.).
        macro_events: Upcoming macroeconomic events.
        news: Recent news headlines with sentiment.
        dxy_series: Dollar Index (DXY) history.
        vix_series: VIX volatility index history.
        eem_series: Emerging markets ETF history.
        fed_dot_plot: Federal Reserve dot plot projections.
        fed_dot_source_id: Source ID for dot plot.
        next_fomc: Next FOMC meeting date.
        rate_differential: TPM - Fed Funds rate differential.
        sources: Source registry for citations.
        usdclp_intraday: Optional intraday USD/CLP data (if available).
        copper_features: Optional derived copper features (volatility, RSI, etc.).

    Example:
        >>> from forex_core.data import DataLoader
        >>> loader = DataLoader()
        >>> bundle = loader.load()
        >>> print(f"USD/CLP: {bundle.indicators['usdclp_spot'].value}")
        >>> print(f"Latest: {bundle.usdclp_series.iloc[-1]}")
        >>> print(f"Sources: {len(bundle.sources)}")
        >>> if bundle.copper_features:
        ...     print(f"Copper volatility: {bundle.copper_features['copper_volatility_20d'].iloc[-1]:.3f}")
    """

    usdclp_series: pd.Series
    copper_series: pd.Series
    tpm_series: pd.Series
    inflation_series: pd.Series
    indicators: Dict[str, Indicator]
    macro_events: List[MacroEvent]
    news: List[NewsHeadline]
    dxy_series: pd.Series
    vix_series: pd.Series
    eem_series: pd.Series
    fed_dot_plot: Dict[str, float]
    fed_dot_source_id: int
    next_fomc: Optional[datetime]
    rate_differential: float
    sources: SourceRegistry
    usdclp_intraday: Optional[pd.Series] = None
    copper_features: Optional[Dict[str, pd.Series]] = None
    chilean_indicators: Optional[Dict[str, pd.Series]] = None
    china_pmi: Optional[pd.Series] = None
    afp_flows: Optional[pd.Series] = None
    lme_inventory: Optional[pd.Series] = None


class DataLoader:
    """
    Main data orchestrator - fetches all data needed for forecasting.

    Coordinates multiple data providers, handles errors gracefully,
    maintains a data warehouse, and tracks all sources for citations.

    Example:
        >>> from forex_core.config import get_settings
        >>> loader = DataLoader(get_settings())
        >>> bundle = loader.load()
        >>>
        >>> # Access data
        >>> print(f"USD/CLP spot: {bundle.indicators['usdclp_spot'].value}")
        >>> print(f"DXY latest: {bundle.dxy_series.iloc[-1]:.2f}")
        >>> print(f"Next events: {len(bundle.macro_events)}")
        >>>
        >>> # Export sources
        >>> print(bundle.sources.as_markdown())
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize data loader with all providers.

        Args:
            settings: Application settings. If None, uses get_settings().

        Example:
            >>> from forex_core.config import get_settings
            >>> loader = DataLoader(get_settings())
        """
        self.settings = settings or get_settings()
        self.sources = SourceRegistry()
        self.mindicador = MindicadorClient(self.settings)
        self.warehouse = Warehouse(self.settings)
        self.macro_calendar = MacroCalendarClient(self.settings)
        self.backup_calendar = BackupMacroCalendarClient(self.settings)
        self.federal_reserve = FederalReserveClient(self.settings)
        self.xe = XeClient(self.settings)
        self.yahoo = YahooClient(self.settings)
        self.copper_client = CopperPricesClient(self.settings)

        # Optional providers (require API keys)
        self.alpha_client: Optional[AlphaVantageClient] = None
        if self.settings.alphavantage_api_key:
            self.alpha_client = AlphaVantageClient(self.settings)
            logger.info("AlphaVantage client initialized")

        self.fred: Optional[FredClient] = None
        if self.settings.fred_api_key:
            self.fred = FredClient(self.settings)
            logger.info("FRED client initialized")

        # Use NewsAggregator for resilient multi-source news fetching
        from forex_core.data.providers.news_aggregator import NewsAggregator
        self.news_aggregator = NewsAggregator(self.settings)
        logger.info("NewsAggregator initialized with multi-source fallback")

        # NEW: Chilean economic indicator providers
        self.bcentral = BancoCentralProvider()
        logger.info("Banco Central provider initialized")

        self.china_pmi: Optional[ChinaPMIProvider] = None
        if self.settings.fred_api_key:
            self.china_pmi = ChinaPMIProvider(self.settings.fred_api_key)
            logger.info("China PMI provider initialized")

        self.afp_provider = AFPFlowProvider()
        logger.info("AFP flows provider initialized")

        self._fed_indicator: Optional[Indicator] = None

    def load(self) -> DataBundle:
        """
        Load complete dataset from all providers.

        Orchestrates data loading from:
        1. MindicadorCL (Chilean indicators)
        2. XE.com (spot rates)
        3. Yahoo Finance (market indices)
        4. Federal Reserve (FOMC calendar, projections)
        5. FRED (optional - US economic data)
        6. Alpha Vantage (optional - intraday forex)
        7. Macro calendar (economic events)
        8. NewsAPI (optional - news sentiment)
        9. World Bank (GDP data)

        Returns:
            DataBundle with all loaded data and source registry.

        Raises:
            httpx.HTTPStatusError: If critical data sources fail.

        Example:
            >>> loader = DataLoader()
            >>> bundle = loader.load()
            >>> print(f"Data loaded from {len(bundle.sources)} sources")
            >>> print(f"USD/CLP series: {len(bundle.usdclp_series)} days")
            >>> print(f"Upcoming events: {len(bundle.macro_events)}")
        """
        logger.info("Starting data load orchestration")

        # Load Chilean indicators
        usdclp_series = self._usdclp_series()
        usdclp_intraday = self._usdclp_intraday()

        tpm_indicator = self._indicator_from_mindicador(
            "tpm", "Tasa Política Monetaria (TPM)"
        )
        ipc_indicator = self._indicator_from_mindicador("ipc", "Inflación IPC mensual")

        tpm_series = self._indicator_series("tpm", alias="tpm_chile")
        inflation_series = self._indicator_series("ipc", alias="ipc_chile")

        # Load copper data with enhanced features (Yahoo Finance primary, FRED backup)
        copper_series, copper_indicator, copper_features = self._load_copper_data()

        indicators = {
            "usdclp_spot": self._usdclp_spot(),
            "copper": copper_indicator,
            "tpm": tpm_indicator,
            "ipc": ipc_indicator,
        }

        # Load XE.com spot rate
        xe_rate, xe_timestamp = self.xe.fetch_rate()
        xe_source = self.sources.add(
            category="Datos de mercado",
            name="XE.com Mid-Market USDCLP",
            url="https://www.xe.com/currencyconverter/convert/?Amount=1&From=USD&To=CLP",
            timestamp=xe_timestamp,
            note="Referencia internacional",
        )
        indicators["xe_spot"] = Indicator(
            name="USD/CLP Xe mid",
            value=float(xe_rate),
            unit="CLP",
            timestamp=xe_timestamp,
            source_id=xe_source,
        )

        # Load market indices from Yahoo Finance
        dxy_series = self.yahoo.fetch_series("DX=F", range_window="10y")
        dxy_series = self.warehouse.upsert_series("dxy_index", dxy_series)
        source_id_dxy = self.sources.add(
            category="Datos de mercado",
            name="Yahoo Finance - DX=F",
            url="https://finance.yahoo.com/quote/DX=F",
            timestamp=dxy_series.index[-1].to_pydatetime(),
            note="Índice DXY (futuros ICE)",
        )

        vix_series = self.yahoo.fetch_series("^VIX")
        vix_series = self.warehouse.upsert_series("vix_index", vix_series)
        self.sources.add(
            category="Datos de mercado",
            name="Yahoo Finance - ^VIX",
            url="https://finance.yahoo.com/quote/%5EVIX",
            timestamp=vix_series.index[-1].to_pydatetime(),
            note="Índice de volatilidad implícita",
        )

        eem_series = self.yahoo.fetch_series("EEM")
        eem_series = self.warehouse.upsert_series("eem_etf", eem_series)
        self.sources.add(
            category="Datos de mercado",
            name="Yahoo Finance - EEM",
            url="https://finance.yahoo.com/quote/EEM",
            timestamp=eem_series.index[-1].to_pydatetime(),
            note="ETF flujos emergentes",
        )

        # Load Federal Reserve data
        fed_dot_plot = self.federal_reserve.dot_plot_medians()
        source_id_dot = self.sources.add(
            category="Pronósticos institucionales",
            name="Federal Reserve SEP",
            url=self.federal_reserve.latest_projection_links()[1],
            timestamp=datetime.utcnow(),
            note="Medianas dot-plot federal funds",
        )
        next_fomc = self.federal_reserve.next_meeting()
        self.sources.add(
            category="Contexto macro",
            name="Federal Reserve FOMC calendar",
            url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            timestamp=datetime.utcnow(),
            note="Próxima reunión FOMC",
        )

        # Calculate rate differential
        rate_diff = self._rate_differential(indicators["tpm"])

        # Load macro events and news
        macro_events = self._macro_events()
        news = self._news()

        # Add DXY indicator
        indicators["dxy"] = Indicator(
            name="Índice DXY",
            value=float(dxy_series.iloc[-1]),
            unit="pts",
            timestamp=dxy_series.index[-1].to_pydatetime(),
            source_id=source_id_dxy,
        )

        # Optional: FRED data
        if self.fred:
            fed_value = self._fed_target_indicator()
            if fed_value:
                indicators["fed_target"] = fed_value

        # Optional: World Bank GDP
        pib_indicator = self._worldbank_gdp()
        if pib_indicator:
            indicators["pib"] = pib_indicator

        # NEW: Load Chilean economic indicators
        chilean_indicators = self.load_chilean_indicators()

        # NEW: Load China PMI (copper demand proxy)
        china_pmi = self.load_china_indicators()

        # NEW: Load AFP flows
        afp_flows = self.load_afp_flows()

        # NEW: Load LME inventory
        lme_inventory = self.load_lme_inventory()

        bundle = DataBundle(
            usdclp_series=usdclp_series,
            usdclp_intraday=usdclp_intraday,
            copper_series=copper_series,
            tpm_series=tpm_series,
            inflation_series=inflation_series,
            indicators=indicators,
            macro_events=macro_events,
            news=news,
            dxy_series=dxy_series,
            vix_series=vix_series,
            eem_series=eem_series,
            fed_dot_plot=fed_dot_plot,
            fed_dot_source_id=source_id_dot,
            next_fomc=next_fomc,
            rate_differential=rate_diff,
            sources=self.sources,
            copper_features=copper_features,
            chilean_indicators=chilean_indicators,
            china_pmi=china_pmi,
            afp_flows=afp_flows,
            lme_inventory=lme_inventory,
        )

        logger.info(
            f"Data load complete: {len(self.sources)} sources, "
            f"{len(macro_events)} events, {len(news)} news"
        )
        return bundle

    def _indicator_from_mindicador(self, code: str, label: str) -> Indicator:
        """Extract latest indicator from MindicadorCL."""
        payload = self.mindicador.get_latest()
        indicator = payload.get(code)
        timestamp = datetime.fromisoformat(indicator["fecha"].replace("Z", "+00:00"))
        source_id = self.sources.add(
            category="Datos de mercado",
            name=f"Mindicador - {label}",
            url=f"https://mindicador.cl/api/{code}",
            timestamp=timestamp,
            note="Banco Central de Chile (vía mindicador.cl)",
        )
        return Indicator(
            name=label,
            value=float(indicator["valor"]),
            unit=indicator.get("unidad_medida", ""),
            timestamp=timestamp,
            source_id=source_id,
        )

    def _usdclp_spot(self) -> Indicator:
        """Get current USD/CLP spot rate from MindicadorCL."""
        payload = self.mindicador.get_latest()
        indicator = payload["dolar"]
        timestamp = datetime.fromisoformat(indicator["fecha"].replace("Z", "+00:00"))
        source_id = self.sources.add(
            category="Datos de mercado",
            name="Mindicador - Dólar observado",
            url="https://mindicador.cl/api/dolar",
            timestamp=timestamp,
            note="Tipo de cambio USD/CLP Banco Central",
        )
        return Indicator(
            name="USD/CLP spot",
            value=float(indicator["valor"]),
            unit="CLP",
            timestamp=timestamp,
            source_id=source_id,
        )

    def _indicator_series(
        self, code: str, *, alias: Optional[str] = None, years: int = 5
    ) -> pd.Series:
        """Load historical series for a MindicadorCL indicator."""
        current_year = datetime.utcnow().year
        collected = []
        for year in range(current_year - (years - 1), current_year + 1):
            payload = self.mindicador.get_indicator(code, year)
            entries = payload.get("serie", [])
            data = {
                datetime.fromisoformat(item["fecha"].replace("Z", "+00:00")): item[
                    "valor"
                ]
                for item in entries
            }
            collected.append(pd.Series(data))

        full = pd.concat(collected).sort_index()
        full = full[~full.index.duplicated(keep="last")]
        name = alias or code
        stored = self.warehouse.upsert_series(name, full)
        return stored

    def _usdclp_series(self) -> pd.Series:
        """Load 6 years of USD/CLP daily data."""
        return self._indicator_series("dolar", alias="usdclp_daily", years=6)

    def _usdclp_intraday(self) -> Optional[pd.Series]:
        """Load intraday USD/CLP data if AlphaVantage available."""
        if not self.alpha_client:
            return None
        try:
            series = self.alpha_client.fetch_intraday()
            stored = self.warehouse.upsert_series("usdclp_intraday_60min", series)
            return stored
        except Exception as exc:
            logger.warning(f"No se pudo obtener intradía AlphaVantage: {exc}")
            return None

    def _macro_events(self) -> List[MacroEvent]:
        """Load upcoming macro events with fallback to backup source."""
        source_id = self.sources.add(
            category="Contexto macro",
            name="ForexFactory calendar",
            url=self.settings.macro_events_url,
            timestamp=datetime.utcnow(),
            note="Eventos macro próximos 7 días",
        )
        events = self.macro_calendar.upcoming_events(
            countries=("USD", "CAD", "CNY", "EUR"),
            days=7,
            source_id=source_id,
        )

        # Fallback to backup source if primary fails
        if not events:
            logger.warning("Primary macro calendar empty, using backup")
            backup_id = self.sources.add(
                category="Contexto macro",
                name="ForexFactory mirror",
                url="https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
                timestamp=datetime.utcnow(),
                note="Fuente secundaria calendario macro",
            )
            events = self.backup_calendar.upcoming_events(
                countries=("USD", "CAD", "CNY", "EUR"),
                days=7,
                source_id=backup_id,
            )
        return events

    def _news(self) -> List[NewsHeadline]:
        """
        Load recent news using multi-source aggregator with fallback.

        Uses NewsAggregator which tries multiple sources in order:
        1. NewsAPI.org (100 requests/day)
        2. NewsData.io (200 requests/day)
        3. RSS Feeds (unlimited)
        4. Empty list (non-blocking - forecast continues without news)

        This method is resilient and will never cause forecast failures.
        """
        try:
            articles = self.news_aggregator.fetch_latest(hours=48)
            enriched: List[NewsHeadline] = []
            for article in articles:
                source_id = self.sources.add(
                    category="Contexto macro",
                    name=f"{article.source} - {article.title[:60]}",
                    url=article.url,
                    timestamp=article.published_at,
                    note="Cobertura geopolítica/noticias cobre",
                )
                article.source_id = source_id
                enriched.append(article)
            return enriched
        except Exception as e:
            logger.error(f"NewsAggregator failed unexpectedly: {e}. Continuing without news.")
            return []

    def _rate_differential(self, tpm: Indicator) -> float:
        """Calculate TPM - Fed Funds differential."""
        fed = self._fed_target_indicator()
        if not fed:
            return float("nan")
        return tpm.value - fed.value

    def _fed_target_indicator(self) -> Optional[Indicator]:
        """Get Fed Funds upper target rate from FRED."""
        if self._fed_indicator:
            return self._fed_indicator
        if not self.fred:
            return None

        df = self.fred.get_series(
            "DFEDTARU", observation_start=datetime.utcnow().date() - timedelta(days=60)
        )
        latest = float(df.iloc[-1, 0])
        source_id = self.sources.add(
            category="Datos de mercado",
            name="FRED - Federal Funds Upper Target",
            url="https://fred.stlouisfed.org/series/DFEDTARU",
            timestamp=df.index[-1].to_pydatetime(),
            note="Rango superior Fed funds",
        )
        indicator = Indicator(
            name="Fed Funds (rango superior)",
            value=latest,
            unit="%",
            timestamp=df.index[-1].to_pydatetime(),
            source_id=source_id,
        )
        self._fed_indicator = indicator
        return indicator

    def load_chilean_indicators(self) -> Dict[str, pd.Series]:
        """
        Load all Chilean economic indicators.

        Includes:
        - Trade Balance (monthly)
        - IMACEC YoY growth (monthly)
        - Current Account (quarterly)

        Returns:
            Dictionary with Chilean indicator series
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)  # 2 years of data

        indicators = {}

        try:
            # Trade balance (monthly)
            trade_balance = self.bcentral.get_trade_balance(start_date, end_date)
            if not trade_balance.empty:
                stored = self.warehouse.upsert_series("chile_trade_balance", trade_balance)
                indicators["trade_balance"] = stored
                source_id = self.sources.add(
                    category="Datos económicos Chile",
                    name="BCCh - Balanza Comercial",
                    url="https://si3.bcentral.cl/Siete",
                    timestamp=trade_balance.index[-1].to_pydatetime(),
                    note="Balanza comercial mensual (millones CLP)"
                )
                logger.info(f"Trade Balance: {len(trade_balance)} observations")

            # IMACEC YoY growth (monthly)
            imacec = self.bcentral.get_imacec_yoy(start_date, end_date)
            if not imacec.empty:
                stored = self.warehouse.upsert_series("chile_imacec_yoy", imacec)
                indicators["imacec_yoy"] = stored
                source_id = self.sources.add(
                    category="Datos económicos Chile",
                    name="BCCh - IMACEC YoY",
                    url="https://si3.bcentral.cl/Siete",
                    timestamp=imacec.index[-1].to_pydatetime(),
                    note="Índice Mensual de Actividad Económica (var. % anual)"
                )
                logger.info(f"IMACEC YoY: {len(imacec)} observations")

            # Current Account (quarterly)
            current_account = self.bcentral.get_current_account(start_date, end_date)
            if not current_account.empty:
                stored = self.warehouse.upsert_series("chile_current_account", current_account)
                indicators["current_account"] = stored
                source_id = self.sources.add(
                    category="Datos económicos Chile",
                    name="BCCh - Cuenta Corriente",
                    url="https://si3.bcentral.cl/Siete",
                    timestamp=current_account.index[-1].to_pydatetime(),
                    note="Cuenta corriente trimestral (millones CLP)"
                )
                logger.info(f"Current Account: {len(current_account)} observations")

        except Exception as e:
            logger.error(f"Failed to load Chilean indicators from BCCh: {e}")

        logger.info(f"Loaded {len(indicators)} Chilean indicators")
        return indicators

    def load_china_indicators(self) -> Optional[pd.Series]:
        """
        Load China PMI data (copper demand proxy).

        Returns:
            China PMI series or None if unavailable
        """
        if not self.china_pmi:
            logger.warning("China PMI provider not available (no FRED API key)")
            return None

        try:
            # Get manufacturing PMI
            pmi = self.china_pmi.get_manufacturing_pmi()
            if not pmi.empty:
                stored = self.warehouse.upsert_series("china_pmi", pmi)
                source_id = self.sources.add(
                    category="Datos internacionales",
                    name="FRED - China Manufacturing PMI",
                    url="https://fred.stlouisfed.org/series/MPMICN",
                    timestamp=pmi.index[-1].to_pydatetime(),
                    note="PMI manufacturero China (>50 = expansión)"
                )
                logger.info(f"China PMI: {len(pmi)} observations, latest: {pmi.iloc[-1]:.1f}")
                return stored

        except Exception as e:
            logger.error(f"Failed to load China PMI: {e}")

        return None

    def load_afp_flows(self) -> Optional[pd.Series]:
        """
        Load AFP international investment flows.

        Returns:
            AFP flows series or None if unavailable
        """
        try:
            flows = self.afp_provider.get_net_international_flows()
            if not flows.empty:
                stored = self.warehouse.upsert_series("afp_flows", flows)
                source_id = self.sources.add(
                    category="Flujos de capital",
                    name="Superintendencia de Pensiones - Flujos AFP",
                    url="https://www.spensiones.cl",
                    timestamp=flows.index[-1].to_pydatetime(),
                    note="Flujos netos inversión internacional AFP (millones USD)"
                )
                logger.info(f"AFP Flows: {len(flows)} observations")
                return stored

        except Exception as e:
            logger.error(f"Failed to load AFP flows: {e}")

        return None

    def load_lme_inventory(self) -> Optional[pd.Series]:
        """
        Load LME copper inventory data.

        Returns:
            LME inventory series or None if unavailable
        """
        try:
            inventory = self.copper_client.get_lme_inventory()
            if not inventory.empty:
                stored = self.warehouse.upsert_series("lme_copper_inventory", inventory)
                source_id = self.sources.add(
                    category="Datos de mercado",
                    name="FRED - LME Copper Warehouse Stocks",
                    url="https://fred.stlouisfed.org/series/WMLMEBCMTN",
                    timestamp=inventory.index[-1].to_pydatetime(),
                    note="Inventario LME cobre (toneladas métricas)"
                )
                logger.info(f"LME Inventory: {len(inventory)} observations")
                return stored

        except Exception as e:
            logger.error(f"Failed to load LME inventory: {e}")

        return None

    def _worldbank_gdp(self) -> Optional[Indicator]:
        """Fetch latest Chilean GDP growth from World Bank API."""
        url = "https://api.worldbank.org/v2/country/CHL/indicator/NY.GDP.MKTP.KD.ZG"
        params = {"format": "json", "per_page": 5}

        try:
            response = httpx.get(
                url,
                params=params,
                timeout=20,
                proxy=self.settings.proxy,
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) < 2:
                return None

            entries = data[1]
            for entry in entries:
                value = entry.get("value")
                if value is not None:
                    date = datetime.strptime(entry["date"], "%Y")
                    source_id = self.sources.add(
                        category="Contexto macro",
                        name="Banco Mundial - PIB Chile",
                        url=f"{url}?format=json",
                        timestamp=datetime.utcnow(),
                        note="Crecimiento PIB real anual",
                    )
                    return Indicator(
                        name="PIB Chile (var. %)",
                        value=float(value),
                        unit="%",
                        timestamp=date,
                        source_id=source_id,
                    )
        except Exception as exc:
            logger.warning(f"Could not fetch World Bank GDP: {exc}")

        return None

    def _load_copper_data(
        self,
    ) -> tuple[pd.Series, Indicator, Optional[Dict[str, pd.Series]]]:
        """
        Load copper price data with enhanced features.

        Uses CopperPricesClient with dual-source fallback:
        1. Yahoo Finance HG=F (primary - daily updates)
        2. FRED PCOPPUSDM (backup - monthly updates)

        Returns:
            Tuple of (copper_series, copper_indicator, copper_features):
            - copper_series: Historical price series stored in warehouse
            - copper_indicator: Latest copper price as Indicator
            - copper_features: Dict of derived features (volatility, RSI, etc.)
                              or None if feature computation fails

        Example:
            >>> series, indicator, features = loader._load_copper_data()
            >>> print(f"Copper: ${indicator.value:.2f} USD/lb")
            >>> print(f"20d volatility: {features['copper_volatility_20d'].iloc[-1]:.3f}")
        """
        try:
            # Fetch 5 years of copper price data
            logger.info("Loading copper prices with enhanced features")
            copper_series_raw = self.copper_client.fetch_series(years=5)

            # Store in warehouse for caching
            copper_series = self.warehouse.upsert_series("copper_hgf_usd_lb", copper_series_raw)

            # Register source
            source_id = self.sources.add(
                category="Datos de mercado",
                name="Yahoo Finance - HG=F (Copper Futures)",
                url="https://finance.yahoo.com/quote/HG=F",
                timestamp=copper_series.index[-1].to_pydatetime(),
                note="Futuros de cobre COMEX (USD/libra)",
            )

            # Get latest copper indicator
            copper_indicator = self.copper_client.get_latest_indicator(source_id=source_id)

            # Compute derived features
            try:
                copper_features = self.copper_client.compute_features(copper_series)

                # Add correlation with USD/CLP if we have the data
                try:
                    usdclp_for_corr = self._usdclp_series()
                    correlation = self.copper_client.compute_correlation_with_usdclp(
                        copper_series, usdclp_for_corr, window=90
                    )
                    copper_features["copper_usdclp_correlation_90d"] = correlation
                    logger.info(
                        f"Copper-USDCLP correlation (90d avg): {correlation.mean():.3f}"
                    )
                except Exception as e:
                    logger.warning(f"Could not compute copper-USDCLP correlation: {e}")

                logger.info(
                    f"Computed {len(copper_features)} copper features "
                    f"(vol_20d mean: {copper_features['copper_volatility_20d'].mean():.3f})"
                )
            except Exception as e:
                logger.warning(f"Could not compute copper features: {e}")
                copper_features = None

            return copper_series, copper_indicator, copper_features

        except Exception as e:
            logger.error(f"Failed to load copper data: {e}")
            # Fallback: try to use cached data from warehouse
            try:
                logger.warning("Attempting to use cached copper data from warehouse")
                copper_series = self.warehouse.get_series("copper_hgf_usd_lb")
                if copper_series is None or len(copper_series) == 0:
                    raise ValueError("No cached copper data available")

                # Create indicator from cached data
                source_id = self.sources.add(
                    category="Datos de mercado",
                    name="Copper (cached)",
                    url="",
                    timestamp=copper_series.index[-1].to_pydatetime(),
                    note="Datos en caché (fuente principal no disponible)",
                )
                copper_indicator = Indicator(
                    name="Precio del cobre (cached)",
                    value=float(copper_series.iloc[-1]),
                    unit="USD/lb",
                    timestamp=copper_series.index[-1].to_pydatetime(),
                    source_id=source_id,
                )

                logger.info(f"Using {len(copper_series)} cached copper data points")
                return copper_series, copper_indicator, None

            except Exception as cache_error:
                logger.error(f"Cached copper data also unavailable: {cache_error}")
                # Last resort: create empty series with NaN to not break pipeline
                logger.warning("Creating empty copper series - forecasts may be degraded")
                empty_series = pd.Series(dtype=float, name="copper_usd_lb")

                source_id = self.sources.add(
                    category="Datos de mercado",
                    name="Copper (unavailable)",
                    url="",
                    timestamp=datetime.utcnow(),
                    note="Datos de cobre no disponibles",
                )
                empty_indicator = Indicator(
                    name="Precio del cobre (N/A)",
                    value=float("nan"),
                    unit="USD/lb",
                    timestamp=datetime.utcnow(),
                    source_id=source_id,
                )

                return empty_series, empty_indicator, None


__all__ = ["DataBundle", "DataLoader"]
