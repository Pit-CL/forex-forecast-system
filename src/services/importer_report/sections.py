"""
Report section generators for importer report.

This module provides functions to generate individual sections
of the comprehensive importer macro report.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from forex_core.data import DataBundle
from forex_core.data.models import ForecastPackage
from forex_core.utils.logging import logger

from .analysis import (
    PESTELAnalysis,
    PorterForces,
    SectorAnalysis,
)


def generate_executive_summary(
    bundle: DataBundle,
    forecast_7d: ForecastPackage,
    forecast_12m: ForecastPackage,
    pestel: PESTELAnalysis,
    porter: PorterForces,
) -> Dict[str, Any]:
    """
    Generate executive summary section.

    Provides high-level overview of current situation, forecasts,
    and key recommendations for decision-makers.

    Args:
        bundle: Current market data.
        forecast_7d: 7-day forecast.
        forecast_12m: 12-month forecast.
        pestel: PESTEL analysis.
        porter: Porter's Five Forces analysis.

    Returns:
        Dictionary with summary content.

    Example:
        >>> summary = generate_executive_summary(bundle, fc_7d, fc_12m, pestel, porter)
        >>> print(summary['headline'])
    """
    logger.info("Generating executive summary")

    usdclp_current = bundle.indicators.get("usdclp_spot", {}).get("value", 0)
    usdclp_7d = forecast_7d.series[-1].mean
    usdclp_12m = forecast_12m.series[-1].mean

    # Calculate changes
    change_7d_pct = ((usdclp_7d - usdclp_current) / usdclp_current) * 100
    change_12m_pct = ((usdclp_12m - usdclp_current) / usdclp_current) * 100

    # Determine trend
    if change_12m_pct > 2:
        trend = "depreciación del peso"
        impact = "presión al alza en costos de importación"
    elif change_12m_pct < -2:
        trend = "apreciación del peso"
        impact = "oportunidad de reducción de costos"
    else:
        trend = "estabilidad del tipo de cambio"
        impact = "condiciones predecibles para planificación"

    headline = (
        f"USD/CLP se proyecta con {trend} hacia ${usdclp_12m:.0f} "
        f"en 12 meses ({change_12m_pct:+.1f}%), generando {impact}."
    )

    key_points = [
        f"Tipo de cambio actual: ${usdclp_current:.2f}",
        f"Proyección 7 días: ${usdclp_7d:.2f} ({change_7d_pct:+.1f}%)",
        f"Proyección 12 meses: ${usdclp_12m:.2f} ({change_12m_pct:+.1f}%)",
        f"Atractivo del sector importador: {porter.overall_attractiveness:.1f}/5.0",
    ]

    recommendations = [
        "Implementar estrategia de cobertura cambiaria para contratos mayores a 90 días",
        "Monitorear semanalmente proyecciones y ajustar tácticas de compra",
        "Diversificar base de proveedores para mitigar riesgos geopolíticos",
    ]

    return {
        "headline": headline,
        "key_points": key_points,
        "recommendations": recommendations,
        "generated_at": datetime.now().isoformat(),
    }


def generate_current_situation(bundle: DataBundle) -> Dict[str, Any]:
    """
    Generate current situation section.

    Summarizes current market conditions, indicators, and recent events.

    Args:
        bundle: Current market data bundle.

    Returns:
        Dictionary with current situation content.
    """
    logger.info("Generating current situation section")

    # Extract key indicators
    usdclp = bundle.indicators.get("usdclp_spot", {}).get("value", 0)
    copper = bundle.indicators.get("copper_price", {}).get("value", 0)
    tpm = bundle.indicators.get("tpm", {}).get("value", 0)
    ipc = bundle.indicators.get("ipc_chile", {}).get("value", 0)

    indicators_summary = {
        "USD/CLP": f"${usdclp:.2f}",
        "Cobre (USD/lb)": f"${copper:.2f}" if copper > 0 else "N/A",
        "TPM": f"{tpm:.2f}%" if tpm > 0 else "N/A",
        "IPC (YoY)": f"{ipc:.2f}%" if ipc > 0 else "N/A",
    }

    # Recent news headlines (if available)
    recent_news = []
    if bundle.news:
        recent_news = [
            {"title": news.title, "date": news.published_at}
            for news in bundle.news[:5]
        ]

    # Upcoming events
    upcoming_events = []
    if bundle.events:
        upcoming_events = [
            {
                "title": event.title,
                "date": event.date,
                "impact": event.impact if hasattr(event, "impact") else "medium",
            }
            for event in bundle.events[:5]
        ]

    return {
        "indicators": indicators_summary,
        "news": recent_news,
        "events": upcoming_events,
        "data_sources": len(bundle.sources),
        "generated_at": datetime.now().isoformat(),
    }


def generate_forecast_section(
    forecast: ForecastPackage,
    horizon: str,
    bundle: DataBundle,
) -> Dict[str, Any]:
    """
    Generate forecast section (either 7d or 12m).

    Args:
        forecast: Forecast package.
        horizon: "7d" or "12m".
        bundle: Current market data.

    Returns:
        Dictionary with forecast section content.
    """
    logger.info(f"Generating {horizon} forecast section")

    usdclp_current = bundle.indicators.get("usdclp_spot", {}).get("value", 0)
    usdclp_final = forecast.series[-1].mean
    change_pct = ((usdclp_final - usdclp_current) / usdclp_current) * 100

    # Extract forecast points
    forecast_points = [
        {
            "date": point.date.isoformat(),
            "mean": round(point.mean, 2),
            "lower": round(point.lower, 2),
            "upper": round(point.upper, 2),
        }
        for point in forecast.series
    ]

    # Analysis
    if abs(change_pct) < 2:
        direction = "estabilidad"
        interpretation = "Los modelos proyectan un tipo de cambio estable con baja volatilidad."
    elif change_pct > 0:
        direction = "depreciación"
        interpretation = (
            f"Los modelos proyectan una depreciación del peso chileno de {change_pct:.1f}%, "
            "lo que incrementaría los costos de importación."
        )
    else:
        direction = "apreciación"
        interpretation = (
            f"Los modelos proyectan una apreciación del peso chileno de {abs(change_pct):.1f}%, "
            "lo que reduciría los costos de importación."
        )

    return {
        "horizon": horizon,
        "current_value": round(usdclp_current, 2),
        "final_value": round(usdclp_final, 2),
        "change_percent": round(change_pct, 2),
        "direction": direction,
        "interpretation": interpretation,
        "forecast_points": forecast_points,
        "confidence_interval": "95%",
        "generated_at": datetime.now().isoformat(),
    }


def generate_risk_matrix(
    bundle: DataBundle,
    forecast_7d: ForecastPackage,
    forecast_12m: ForecastPackage,
    pestel: PESTELAnalysis,
) -> Dict[str, Any]:
    """
    Generate risk matrix section.

    Identifies and prioritizes risks for importers.

    Args:
        bundle: Current market data.
        forecast_7d: 7-day forecast.
        forecast_12m: 12-month forecast.
        pestel: PESTEL analysis.

    Returns:
        Dictionary with risk matrix content.
    """
    logger.info("Generating risk matrix")

    # Define risk categories and assessments
    risks = [
        {
            "category": "Riesgo Cambiario",
            "probability": "Alta",
            "impact": "Alto",
            "description": "Volatilidad del USD/CLP afecta costos de importación",
            "mitigation": "Implementar coberturas forward o opciones",
        },
        {
            "category": "Riesgo Geopolítico",
            "probability": "Media",
            "impact": "Alto",
            "description": "Tensiones comerciales globales afectan cadenas de suministro",
            "mitigation": "Diversificar proveedores por región geográfica",
        },
        {
            "category": "Riesgo Regulatorio",
            "probability": "Media",
            "impact": "Medio",
            "description": "Cambios en normativas aduaneras o ambientales",
            "mitigation": "Monitoreo regulatorio continuo y compliance proactivo",
        },
        {
            "category": "Riesgo de Liquidez",
            "probability": "Baja",
            "impact": "Alto",
            "description": "Dificultades para financiar importaciones",
            "mitigation": "Diversificar fuentes de financiamiento",
        },
        {
            "category": "Riesgo de Demanda",
            "probability": "Media",
            "impact": "Medio",
            "description": "Cambios en patrones de consumo afectan ventas",
            "mitigation": "Análisis continuo de mercado y flexibilidad de inventarios",
        },
    ]

    return {
        "risks": risks,
        "priority_risks": [r for r in risks if r["impact"] == "Alto"],
        "generated_at": datetime.now().isoformat(),
    }


def generate_recommendations_section(
    bundle: DataBundle,
    forecast_7d: ForecastPackage,
    forecast_12m: ForecastPackage,
    sector_analyses: list[SectorAnalysis],
) -> Dict[str, Any]:
    """
    Generate strategic recommendations section.

    Provides actionable recommendations based on analysis.

    Args:
        bundle: Current market data.
        forecast_7d: 7-day forecast.
        forecast_12m: 12-month forecast.
        sector_analyses: List of sector analyses.

    Returns:
        Dictionary with recommendations.
    """
    logger.info("Generating recommendations section")

    # Calculate FX trend
    usdclp_current = bundle.indicators.get("usdclp_spot", {}).get("value", 0)
    usdclp_12m = forecast_12m.series[-1].mean
    fx_change = ((usdclp_12m - usdclp_current) / usdclp_current) * 100

    # Strategic recommendations
    strategic = [
        "Desarrollar política de cobertura cambiaria basada en horizonte de planificación",
        "Establecer umbrales de gatillo para coberturas (ej: movimientos >3% en 30 días)",
        "Evaluar relocalización de compras según evolución de costos logísticos",
    ]

    # Tactical recommendations (short-term)
    if fx_change > 2:
        tactical = [
            "Considerar adelantar compras críticas antes de depreciación proyectada",
            "Negociar cláusulas de ajuste cambiario en contratos a plazo",
            "Revisar precios de venta considerando impacto en márgenes",
        ]
    elif fx_change < -2:
        tactical = [
            "Aprovechar apreciación proyectada para optimizar inventarios",
            "Renegociar contratos con proveedores considerando nuevo escenario",
            "Evaluar oportunidades de compra de productos de mayor valor",
        ]
    else:
        tactical = [
            "Mantener política actual con monitoreo quincenal",
            "Preparar planes de contingencia para escenarios de volatilidad",
            "Optimizar capital de trabajo y rotación de inventarios",
        ]

    # Sector-specific recommendations
    sector_specific = {}
    for analysis in sector_analyses:
        sector_specific[analysis.sector_name] = analysis.recommendations[:3]

    return {
        "strategic": strategic,
        "tactical": tactical,
        "sector_specific": sector_specific,
        "review_frequency": "Revisar proyecciones semanalmente, estrategia mensualmente",
        "generated_at": datetime.now().isoformat(),
    }


__all__ = [
    "generate_executive_summary",
    "generate_current_situation",
    "generate_forecast_section",
    "generate_risk_matrix",
    "generate_recommendations_section",
]
