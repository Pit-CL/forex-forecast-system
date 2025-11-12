"""
Fundamental analysis for forex pairs.

This module provides functions for extracting and analyzing quantitative
fundamental factors that drive currency pair movements, including:
- Interest rate differentials (TPM vs Fed Funds)
- Inflation differentials (IPC Chile vs US CPI)
- Terms of trade (copper prices for CLP)
- Currency strength indices (DXY)
- Growth differentials (GDP)

The QuantFactor dataclass standardizes representation of fundamental factors
with current values, trends, and expected impact on the currency pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..data.loader import DataBundle
    from ..data.models import MacroEvent


@dataclass
class QuantFactor:
    """
    Quantitative fundamental factor affecting currency pairs.

    Attributes:
        name: Human-readable factor name (e.g., "USD/CLP Spot", "Copper Price").
        value: Current value of the factor.
        trend: Recent change in the factor (typically % change over 5 days).
                None if not applicable.
        impact: Description of how this factor affects USD/CLP.
        unit: Unit of measurement (e.g., "CLP", "%", "USD/lb", "pts").
        source_id: Reference to data source in SourceRegistry.

    Example:
        >>> factor = QuantFactor(
        ...     name="TPM Chile",
        ...     value=5.75,
        ...     trend=0.25,  # +25 bps
        ...     impact="Alza TPM atrae flujos hacia CLP",
        ...     unit="%",
        ...     source_id=1
        ... )
    """
    name: str
    value: float
    trend: Optional[float]
    impact: str
    unit: str
    source_id: int


def build_quant_factors(factors: Dict[str, QuantFactor]) -> pd.DataFrame:
    """
    Build a formatted DataFrame of quantitative factors for reporting.

    Args:
        factors: Dictionary of QuantFactor objects keyed by factor ID.

    Returns:
        DataFrame with columns:
            - Indicador: Factor name
            - Valor Actual: Current value with unit
            - Tendencia: Trend (% change) or "n/d"
            - Impacto USD/CLP: Description of impact
            - Fuente: Source reference ID

    Example:
        >>> factors = extract_quant_factors(bundle)
        >>> df = build_quant_factors(factors)
        >>> print(df.to_string())
    """
    rows = []
    for factor in factors.values():
        rows.append(
            {
                "Indicador": factor.name,
                "Valor Actual": f"{factor.value:.2f} {factor.unit}",
                "Tendencia": f"{factor.trend:+.2f}%" if factor.trend is not None else "n/d",
                "Impacto USD/CLP": factor.impact,
                "Fuente": f"[{factor.source_id}]",
            }
        )
    return pd.DataFrame(rows)


def macro_events_table(events: List[MacroEvent]) -> pd.DataFrame:
    """
    Build a formatted DataFrame of upcoming macroeconomic events.

    Args:
        events: List of MacroEvent objects.

    Returns:
        DataFrame with columns:
            - Fecha: Event datetime (YYYY-MM-DD HH:MM)
            - Evento: Event title
            - País: Country code
            - Impacto: Impact level (High/Medium/Low)
            - Indicador: Forecast / Previous values
            - Fuente: Source reference ID

    Example:
        >>> events = bundle.macro_events[:10]
        >>> df = macro_events_table(events)
        >>> print(df.to_string())
    """
    rows = []
    for event in events:
        rows.append(
            {
                "Fecha": event.datetime.strftime("%Y-%m-%d %H:%M"),
                "Evento": event.title,
                "País": event.country,
                "Impacto": event.impact,
                "Indicador": f"{event.forecast or '-'} / {event.previous or '-'}",
                "Fuente": f"[{event.source_id}]",
            }
        )
    return pd.DataFrame(rows)


def extract_quant_factors(bundle: DataBundle) -> Dict[str, QuantFactor]:
    """
    Extract quantitative fundamental factors from a DataBundle.

    This function computes current values, recent trends (5-day % change),
    and impact descriptions for key fundamental factors affecting USD/CLP.

    Factors extracted:
        - usdclp: USD/CLP spot rate
        - cobre: Copper price (Chile's main export, terms of trade)
        - tpm: Chilean Central Bank policy rate (TPM)
        - ipc: Chilean inflation (IPC)
        - dxy: US Dollar Index (global USD strength)
        - fed: Federal Reserve target rate
        - pib: Chilean GDP growth
        - xe: USD/CLP cross-check from XE.com

    Args:
        bundle: DataBundle containing indicators and time series.

    Returns:
        Dictionary of QuantFactor objects keyed by factor ID.

    Example:
        >>> from forex_core.data.loader import load_data
        >>> bundle = load_data()
        >>> factors = extract_quant_factors(bundle)
        >>> print(f"Current USD/CLP: {factors['usdclp'].value:.2f}")
        >>> print(f"Copper trend: {factors['cobre'].trend:+.2f}%")

    Notes:
        - Trend is calculated as % change over 5 periods (days for daily data)
        - Optional factors (dxy, fed, pib, xe) return None if not in bundle
        - Uses percent_change utility for consistent calculation
        - Impact descriptions are specific to USD/CLP (adjust for other pairs)
    """
    from ..utils.helpers import percent_change

    usdclp = bundle.indicators["usdclp_spot"]
    copper = bundle.indicators["copper"]
    tpm = bundle.indicators["tpm"]
    ipc = bundle.indicators["ipc"]
    dxy = bundle.indicators.get("dxy")
    fed = bundle.indicators.get("fed_target")
    pib = bundle.indicators.get("pib")
    xe = bundle.indicators.get("xe_spot")

    factors: Dict[str, QuantFactor] = {}

    # USD/CLP spot rate
    usd_return = percent_change(
        usdclp.value,
        bundle.usdclp_series.iloc[-5],
    )
    factors["usdclp"] = QuantFactor(
        name="USD/CLP Spot",
        value=usdclp.value,
        trend=usd_return,
        impact="Movimiento directo del par",
        unit="CLP",
        source_id=usdclp.source_id,
    )

    # Copper (Chile's main export - terms of trade)
    copper_return = percent_change(
        copper.value, bundle.copper_series.iloc[-5]
    )
    factors["cobre"] = QuantFactor(
        name="Libra de cobre",
        value=copper.value,
        trend=copper_return,
        impact="Cobre al alza fortalece CLP (bajista USD/CLP)",
        unit="USD/lb",
        source_id=copper.source_id,
    )

    # TPM (Chilean Central Bank policy rate)
    tpm_change = tpm.value - bundle.tpm_series.iloc[-2]
    factors["tpm"] = QuantFactor(
        name="TPM Chile",
        value=tpm.value,
        trend=tpm_change,
        impact="Alza TPM atrae flujos hacia CLP",
        unit="%",
        source_id=tpm.source_id,
    )

    # IPC (Chilean inflation)
    ipc_change = ipc.value - bundle.inflation_series.iloc[-2]
    factors["ipc"] = QuantFactor(
        name="Inflación IPC mensual",
        value=ipc.value,
        trend=ipc_change,
        impact="Inflación alta presiona depreciación y más hikes",
        unit="%",
        source_id=ipc.source_id,
    )

    # DXY (US Dollar Index - global USD strength)
    if dxy:
        dxy_change = percent_change(dxy.value, bundle.dxy_series.iloc[-5])
        factors["dxy"] = QuantFactor(
            name="DXY Index",
            value=dxy.value,
            trend=dxy_change,
            impact="Dólar global fuerte impulsa USD/CLP",
            unit="pts",
            source_id=dxy.source_id,
        )

    # Fed Funds (US policy rate)
    if fed:
        factors["fed"] = QuantFactor(
            name="Fed funds (rango sup.)",
            value=fed.value,
            trend=None,
            impact="Tasa Fed alta resta atractivo relativo al CLP",
            unit="%",
            source_id=fed.source_id,
        )

    # PIB (Chilean GDP growth)
    if pib:
        factors["pib"] = QuantFactor(
            name="PIB Chile (var anual)",
            value=pib.value,
            trend=None,
            impact="Crecimiento sólido favorece CLP",
            unit="%",
            source_id=pib.source_id,
        )

    # XE spot rate (cross-check)
    if xe:
        spread = percent_change(xe.value, usdclp.value)
        factors["xe"] = QuantFactor(
            name="USD/CLP Xe mid",
            value=xe.value,
            trend=spread,
            impact="Referencia internacional para arbitrajes intradía",
            unit="CLP",
            source_id=xe.source_id,
        )

    return factors


__all__ = [
    "QuantFactor",
    "build_quant_factors",
    "macro_events_table",
    "extract_quant_factors",
]
