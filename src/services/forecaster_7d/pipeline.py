"""
Pipeline orchestration for 7-day forex forecasting.

This module coordinates the complete forecasting workflow:
1. Data loading from multiple sources
2. Ensemble forecast generation
3. Chart creation
4. PDF report generation
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

from .config import get_service_config


def run_forecast_pipeline(
    skip_email: bool = False,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Execute the complete 7-day forecasting pipeline.

    This function orchestrates all steps of the forecasting process:
    1. Load configuration
    2. Fetch data from providers (USD/CLP, macro indicators, news)
    3. Generate 7-day forecast using ensemble models
    4. Create visualization charts
    5. Build comprehensive PDF report
    6. Send email notification (optional)

    Args:
        skip_email: If True, skip email delivery step.
        output_dir: Override default output directory for reports.

    Returns:
        Path to the generated PDF report.

    Raises:
        ValueError: If data loading fails or forecast cannot be generated.
        RuntimeError: If report generation fails.

    Example:
        >>> # Run full pipeline with email
        >>> report_path = run_forecast_pipeline()
        >>> print(f"Report generated: {report_path}")

        >>> # Run without email, custom output
        >>> report_path = run_forecast_pipeline(
        ...     skip_email=True,
        ...     output_dir=Path("./custom_reports")
        ... )
    """
    logger.info("Starting 7-day forecast pipeline")
    start_time = datetime.now()

    # Load configurations
    settings = get_settings()
    service_config = get_service_config()

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

        # Step 2: Generate forecast
        logger.info(f"Generating {service_config.projection_days}-day forecast...")
        forecast, artifacts = _generate_forecast(settings, service_config, bundle)
        logger.info(
            f"Forecast generated: {len(forecast.series)} points, "
            f"final mean: {forecast.series[-1].mean:.2f}"
        )

        # Step 3: Generate charts
        logger.info("Creating visualization charts...")
        chart_paths = _generate_charts(settings, service_config, bundle, forecast)
        logger.info(f"Generated {len(chart_paths)} charts")

        # Step 4: Build report
        logger.info("Building PDF report...")
        report_path = _build_report(
            settings, service_config, bundle, forecast, artifacts, chart_paths
        )
        logger.info(f"Report saved: {report_path}")

        # Step 5: Send email (optional)
        if not skip_email:
            logger.info("Sending email notification...")
            _send_email(settings, report_path)
            logger.success("Email sent successfully")
        else:
            logger.info("Email delivery skipped")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"Pipeline completed in {elapsed:.2f}s")

        return report_path

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


def _generate_forecast(
    settings,
    service_config,
    bundle: DataBundle,
) -> Tuple[ForecastPackage, EnsembleArtifacts]:
    """Generate ensemble forecast using configured models."""
    engine = ForecastEngine(
        config=settings,
        horizon=service_config.horizon,
        steps=service_config.steps,
    )
    return engine.forecast(bundle)


def _generate_charts(
    settings,
    service_config,
    bundle: DataBundle,
    forecast: ForecastPackage,
) -> dict[str, Path]:
    """
    Generate visualization charts for the report.

    NOTE: Chart generation is not yet implemented in forex_core.
    This is a placeholder for when ChartGenerator is available.
    """
    logger.warning("Chart generation not yet implemented - placeholder")
    # TODO: Implement when forex_core.reporting.ChartGenerator is ready
    # from forex_core.reporting import ChartGenerator
    # generator = ChartGenerator(settings)
    # return generator.generate(bundle, forecast, title_suffix=service_config.chart_title_suffix)
    return {}


def _build_report(
    settings,
    service_config,
    bundle: DataBundle,
    forecast: ForecastPackage,
    artifacts: EnsembleArtifacts,
    chart_paths: dict[str, Path],
) -> Path:
    """
    Build PDF report with forecast results.

    NOTE: Report building is not yet implemented in forex_core.
    This is a placeholder for when ReportBuilder is available.
    """
    logger.warning("Report building not yet implemented - placeholder")
    # TODO: Implement when forex_core.reporting.ReportBuilder is ready
    # from forex_core.reporting import ReportBuilder
    # builder = ReportBuilder(settings)
    # return builder.build(
    #     bundle=bundle,
    #     forecast=forecast,
    #     artifacts=artifacts,
    #     chart_paths=chart_paths,
    #     title=service_config.report_title,
    #     filename_prefix=service_config.report_filename_prefix
    # )

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
    # from forex_core.notifications import EmailSender
    # sender = EmailSender(settings)
    # sender.send(
    #     subject=f"Proyección USD/CLP 7 días - {datetime.now():%Y-%m-%d}",
    #     body="Se adjunta la proyección de tipo de cambio para los próximos 7 días.",
    #     attachment_path=report_path
    # )


def validate_forecast(bundle: DataBundle, forecast: ForecastPackage) -> bool:
    """
    Validate forecast results for sanity checks.

    Checks:
    - Forecast has expected number of points
    - Values are within reasonable bounds (> 0)
    - No NaN values
    - Uncertainty intervals are valid (lower < mean < upper)

    Args:
        bundle: Input data bundle.
        forecast: Generated forecast package.

    Returns:
        True if validation passes, False otherwise.

    Example:
        >>> from forex_core.data import DataLoader
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> loader = DataLoader(settings)
        >>> bundle = loader.load()
        >>> # ... generate forecast ...
        >>> is_valid = validate_forecast(bundle, forecast)
    """
    service_config = get_service_config()

    # Check number of forecast points
    if len(forecast.series) != service_config.steps:
        logger.error(
            f"Expected {service_config.steps} forecast points, "
            f"got {len(forecast.series)}"
        )
        return False

    # Check for valid values
    for i, point in enumerate(forecast.series):
        # Check for NaN
        if any(
            v is None or (isinstance(v, float) and v != v)  # NaN check
            for v in [point.mean, point.lower, point.upper]
        ):
            logger.error(f"NaN value at forecast point {i}")
            return False

        # Check for positive values
        if point.mean <= 0:
            logger.error(f"Non-positive mean at forecast point {i}: {point.mean}")
            return False

        # Check interval validity
        if not (point.lower <= point.mean <= point.upper):
            logger.error(
                f"Invalid interval at point {i}: "
                f"lower={point.lower}, mean={point.mean}, upper={point.upper}"
            )
            return False

        # Check reasonable bounds (USD/CLP typically 700-1100)
        if not (500 <= point.mean <= 1500):
            logger.warning(
                f"Unusual forecast value at point {i}: {point.mean:.2f}. "
                "This may indicate data issues."
            )

    logger.success("Forecast validation passed")
    return True


__all__ = ["run_forecast_pipeline", "validate_forecast"]
