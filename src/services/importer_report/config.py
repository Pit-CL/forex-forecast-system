"""
Configuration for importer report service.

This module provides service-specific configuration for the comprehensive
monthly importer macro-economic report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ImporterReportConfig:
    """
    Service-specific configuration for importer report.

    This service generates a comprehensive macro-economic report
    that includes both short-term (7d) and long-term (12m) forecasts,
    plus strategic analysis frameworks.

    Attributes:
        report_title: Report title in Spanish.
        report_filename_prefix: Prefix for output filenames.
        include_7d_forecast: Whether to include 7-day forecast section.
        include_12m_forecast: Whether to include 12-month forecast section.
        include_pestel: Whether to include PESTEL analysis.
        include_porter: Whether to include Porter's Five Forces.
        include_sector_analysis: Whether to include sector-specific analysis.
        target_sectors: List of sectors to analyze (e.g., restaurants, retail).
        report_sections: Ordered list of report sections.
        page_limit: Target page count for report.

    Example:
        >>> config = ImporterReportConfig()
        >>> print(config.report_title)
        'Informe Mensual del Entorno Macroeconómico del Importador'
    """

    # Report metadata
    report_title: str = "Informe Mensual del Entorno Macroeconómico del Importador"
    report_subtitle: str = "Análisis Estratégico y Proyecciones USD/CLP"
    report_filename_prefix: str = "Informe_Entorno_Importador"

    # Report sections toggle
    include_7d_forecast: bool = True
    include_12m_forecast: bool = True
    include_pestel: bool = True
    include_porter: bool = True
    include_sector_analysis: bool = True

    # Sector configuration
    target_sectors: tuple[str, ...] = (
        "Restaurantes",
        "Retail",
        "Manufactura",
        "Tecnología",
    )

    # Report structure
    report_sections: tuple[str, ...] = (
        "executive_summary",
        "current_situation",
        "forecast_7d",
        "forecast_12m",
        "pestel_analysis",
        "porter_forces",
        "sector_analysis",
        "risk_matrix",
        "recommendations",
        "sources",
    )

    # Report configuration
    page_limit: int = 20
    executive_summary_max_words: int = 500

    # Chart configuration
    chart_style: str = "professional"  # Options: professional, simple, detailed
    include_technical_charts: bool = True

    # Language
    language: str = "es"  # Spanish
    currency_format: str = "CLP"


def get_service_config() -> ImporterReportConfig:
    """
    Get the service-specific configuration.

    Returns:
        Frozen configuration instance for importer report.

    Example:
        >>> config = get_service_config()
        >>> assert config.include_pestel is True
    """
    return ImporterReportConfig()


__all__ = ["ImporterReportConfig", "get_service_config"]
