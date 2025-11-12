"""
Pipeline orchestration for comprehensive importer report.

This module coordinates the complete report generation workflow:
1. Data loading
2. Both 7-day and 12-month forecast generation
3. Strategic analysis (PESTEL, Porter, sectors)
4. Comprehensive PDF report (10-20 pages)
5. Email delivery (optional)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from forex_core.config import get_settings
from forex_core.data import DataBundle, DataLoader
from forex_core.data.models import ForecastPackage
from forex_core.forecasting import ForecastEngine, EnsembleArtifacts
from forex_core.utils.logging import logger

from services.forecaster_7d.config import get_service_config as get_7d_config
from services.forecaster_12m.config import get_service_config as get_12m_config
from services.forecaster_12m.pipeline import _resample_to_monthly

from .config import get_service_config
from .analysis import (
    generate_pestel_analysis,
    generate_porter_analysis,
    generate_sector_analysis,
)
from .sections import (
    generate_executive_summary,
    generate_current_situation,
    generate_forecast_section,
    generate_risk_matrix,
    generate_recommendations_section,
)


def run_report_pipeline(
    skip_email: bool = False,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Execute the complete importer report pipeline.

    This function orchestrates all steps of the comprehensive report:
    1. Load configuration
    2. Fetch data from all providers
    3. Generate 7-day forecast (daily)
    4. Generate 12-month forecast (monthly)
    5. Perform strategic analyses (PESTEL, Porter, sectors)
    6. Generate all report sections
    7. Create comprehensive PDF report (10-20 pages)
    8. Send email notification (optional)

    Args:
        skip_email: If True, skip email delivery step.
        output_dir: Override default output directory for reports.

    Returns:
        Path to the generated PDF report.

    Raises:
        ValueError: If data loading fails or forecasts cannot be generated.
        RuntimeError: If report generation fails.

    Example:
        >>> # Run full pipeline with email
        >>> report_path = run_report_pipeline()
        >>> print(f"Report generated: {report_path}")

        >>> # Run without email, custom output
        >>> report_path = run_report_pipeline(
        ...     skip_email=True,
        ...     output_dir=Path("./monthly_reports")
        ... )
    """
    logger.info("Starting comprehensive importer report pipeline")
    start_time = datetime.now()

    # Load configurations
    settings = get_settings()
    service_config = get_service_config()
    config_7d = get_7d_config()
    config_12m = get_12m_config()

    # Override output directory if specified
    if output_dir:
        settings.output_dir = output_dir
        settings.ensure_directories()

    try:
        # Step 1: Load data
        logger.info("Loading data from providers...")
        loader = DataLoader(settings)
        bundle: DataBundle = loader.load()
        logger.info(
            f"Data loaded: {len(bundle.indicators)} indicators, "
            f"{len(bundle.sources)} sources"
        )

        # Step 2: Generate 7-day forecast
        logger.info("Generating 7-day forecast...")
        forecast_7d, artifacts_7d = _generate_7d_forecast(settings, config_7d, bundle)
        logger.info(f"7-day forecast: final value ${forecast_7d.series[-1].mean:.2f}")

        # Step 3: Generate 12-month forecast
        logger.info("Generating 12-month forecast...")
        bundle_monthly = _resample_to_monthly(bundle.copy() if hasattr(bundle, 'copy') else bundle)
        forecast_12m, artifacts_12m = _generate_12m_forecast(
            settings, config_12m, bundle_monthly
        )
        logger.info(f"12-month forecast: final value ${forecast_12m.series[-1].mean:.2f}")

        # Step 4: Perform strategic analyses
        logger.info("Performing strategic analyses...")
        pestel = generate_pestel_analysis(bundle, forecast_7d, forecast_12m)
        porter = generate_porter_analysis(bundle, forecast_7d, forecast_12m)

        sector_analyses = []
        for sector in service_config.target_sectors:
            analysis = generate_sector_analysis(sector, bundle, forecast_7d, forecast_12m)
            sector_analyses.append(analysis)
        logger.info(f"Generated {len(sector_analyses)} sector analyses")

        # Step 5: Generate report sections
        logger.info("Generating report sections...")
        sections_data = _generate_all_sections(
            bundle,
            forecast_7d,
            forecast_12m,
            pestel,
            porter,
            sector_analyses,
        )

        # Step 6: Generate charts
        logger.info("Creating visualization charts...")
        chart_paths = _generate_charts(
            settings,
            service_config,
            bundle,
            forecast_7d,
            forecast_12m,
        )
        logger.info(f"Generated {len(chart_paths)} charts")

        # Step 7: Build comprehensive report
        logger.info("Building comprehensive PDF report...")
        report_path = _build_report(
            settings,
            service_config,
            sections_data,
            chart_paths,
        )
        logger.info(f"Report saved: {report_path}")

        # Step 8: Send email (optional)
        if not skip_email:
            logger.info("Sending email notification...")
            _send_email(settings, report_path)
            logger.success("Email sent successfully")
        else:
            logger.info("Email delivery skipped")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"Report pipeline completed in {elapsed:.2f}s")

        return report_path

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


def _generate_7d_forecast(
    settings,
    config_7d,
    bundle: DataBundle,
) -> Tuple[ForecastPackage, EnsembleArtifacts]:
    """Generate 7-day daily forecast."""
    engine = ForecastEngine(
        config=settings,
        horizon=config_7d.horizon,
        steps=config_7d.steps,
    )
    return engine.forecast(bundle)


def _generate_12m_forecast(
    settings,
    config_12m,
    bundle: DataBundle,
) -> Tuple[ForecastPackage, EnsembleArtifacts]:
    """Generate 12-month monthly forecast."""
    engine = ForecastEngine(
        config=settings,
        horizon=config_12m.horizon,
        steps=config_12m.steps,
    )
    return engine.forecast(bundle)


def _generate_all_sections(
    bundle: DataBundle,
    forecast_7d: ForecastPackage,
    forecast_12m: ForecastPackage,
    pestel,
    porter,
    sector_analyses,
) -> dict:
    """Generate all report sections."""
    sections = {}

    sections["executive_summary"] = generate_executive_summary(
        bundle, forecast_7d, forecast_12m, pestel, porter
    )

    sections["current_situation"] = generate_current_situation(bundle)

    sections["forecast_7d"] = generate_forecast_section(
        forecast_7d, "7d", bundle
    )

    sections["forecast_12m"] = generate_forecast_section(
        forecast_12m, "12m", bundle
    )

    sections["pestel"] = {
        "political": pestel.political,
        "economic": pestel.economic,
        "social": pestel.social,
        "technological": pestel.technological,
        "environmental": pestel.environmental,
        "legal": pestel.legal,
    }

    sections["porter"] = {
        "competitive_rivalry": porter.competitive_rivalry,
        "supplier_power": porter.supplier_power,
        "buyer_power": porter.buyer_power,
        "threat_of_substitution": porter.threat_of_substitution,
        "threat_of_new_entry": porter.threat_of_new_entry,
        "overall_attractiveness": porter.overall_attractiveness,
    }

    sections["sector_analyses"] = [
        {
            "sector": analysis.sector_name,
            "outlook": analysis.outlook,
            "key_trends": analysis.key_trends,
            "fx_sensitivity": analysis.fx_sensitivity,
            "recommendations": analysis.recommendations,
        }
        for analysis in sector_analyses
    ]

    sections["risk_matrix"] = generate_risk_matrix(
        bundle, forecast_7d, forecast_12m, pestel
    )

    sections["recommendations"] = generate_recommendations_section(
        bundle, forecast_7d, forecast_12m, sector_analyses
    )

    sections["sources"] = [
        {
            "name": source.name,
            "type": source.source_type,
            "url": source.url,
        }
        for source in bundle.sources
    ]

    return sections


def _generate_charts(
    settings,
    service_config,
    bundle: DataBundle,
    forecast_7d: ForecastPackage,
    forecast_12m: ForecastPackage,
) -> dict[str, Path]:
    """
    Generate visualization charts for the report.

    NOTE: Chart generation is not yet implemented in forex_core.
    This is a placeholder for when ChartGenerator is available.
    """
    logger.warning("Chart generation not yet implemented - placeholder")
    # TODO: Implement when forex_core.reporting.ChartGenerator is ready
    return {}


def _build_report(
    settings,
    service_config,
    sections_data: dict,
    chart_paths: dict[str, Path],
) -> Path:
    """
    Build comprehensive PDF report.

    NOTE: Report building is not yet implemented in forex_core.
    This is a placeholder for when ReportBuilder is available.
    """
    logger.warning("Report building not yet implemented - placeholder")
    # TODO: Implement when forex_core.reporting.ReportBuilder is ready

    # Temporary: Return placeholder path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return settings.output_dir / f"{service_config.report_filename_prefix}_{timestamp}.pdf"


def _send_email(settings, report_path: Path) -> None:
    """
    Send email notification with report attached.

    NOTE: Email sending is not yet implemented in forex_core.
    This is a placeholder for when EmailSender is available.
    """
    logger.warning("Email sending not yet implemented - placeholder")
    # TODO: Implement when forex_core.notifications.EmailSender is ready


__all__ = ["run_report_pipeline"]
