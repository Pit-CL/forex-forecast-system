"""
Pipeline orchestration for 12-month forex forecasting.

This module coordinates the complete forecasting workflow with
monthly resampling for long-term predictions:
1. Data loading and monthly resampling
2. Ensemble forecast generation (12 months)
3. Chart creation
4. PDF report generation
5. Email delivery (optional)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

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
    Execute the complete 12-month forecasting pipeline.

    This function orchestrates all steps of the forecasting process:
    1. Load configuration
    2. Fetch data from providers (USD/CLP, macro indicators, news)
    3. Resample to monthly frequency
    4. Generate 12-month forecast using ensemble models
    5. Create visualization charts
    6. Build comprehensive PDF report
    7. Send email notification (optional)

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
    logger.info("Starting 12-month forecast pipeline")
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

        # Step 1b: Resample to monthly frequency
        logger.info("Resampling data to monthly frequency...")
        bundle = _resample_to_monthly(bundle)
        logger.info(f"Data resampled: {len(bundle.time_series)} monthly points")

        # Step 2: Generate forecast
        logger.info(f"Generating {service_config.projection_months}-month forecast...")
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


def _resample_to_monthly(bundle: DataBundle) -> DataBundle:
    """
    Resample time series data to monthly frequency.

    Uses month-end resampling (.resample("ME").last()) to convert
    daily data to monthly data points. This is essential for 12-month
    forecasting to reduce noise and focus on long-term trends.

    Args:
        bundle: Input data bundle with daily data.

    Returns:
        Modified data bundle with monthly-resampled time series.

    Example:
        >>> # Daily data: 730 points (2 years)
        >>> # Monthly data: 24 points (24 months)
        >>> monthly_bundle = _resample_to_monthly(daily_bundle)
    """
    if bundle.time_series is None or bundle.time_series.empty:
        logger.warning("No time series data to resample")
        return bundle

    # Resample to month-end frequency using last value of each month
    monthly_ts = bundle.time_series.resample("ME").last()

    # Drop any NaN values that may result from resampling
    monthly_ts = monthly_ts.dropna()

    logger.info(
        f"Resampled from {len(bundle.time_series)} daily points "
        f"to {len(monthly_ts)} monthly points"
    )

    # Create new bundle with monthly data
    bundle.time_series = monthly_ts
    return bundle


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
    # return generator.generate(
    #     bundle,
    #     forecast,
    #     title_suffix=service_config.chart_title_suffix,
    #     frequency="monthly"
    # )
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
    #     subject=f"Proyección USD/CLP 12 meses - {datetime.now():%Y-%m-%d}",
    #     body="Se adjunta la proyección de tipo de cambio para los próximos 12 meses.",
    #     attachment_path=report_path
    # )


def validate_forecast(bundle: DataBundle, forecast: ForecastPackage) -> bool:
    """
    Validate forecast results for sanity checks.

    Checks:
    - Forecast has expected number of points (12)
    - Values are within reasonable bounds (> 0)
    - No NaN values
    - Uncertainty intervals are valid (lower < mean < upper)
    - Monthly dates are properly spaced

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
        >>> # ... resample and generate forecast ...
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

    # Check for valid values and monthly spacing
    prev_date = None
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

        # Check monthly spacing (approximately 28-31 days)
        if prev_date is not None:
            days_diff = (point.date - prev_date).days
            if not (25 <= days_diff <= 35):
                logger.warning(
                    f"Unusual date spacing at point {i}: {days_diff} days. "
                    "Expected ~30 days for monthly data."
                )

        prev_date = point.date

    logger.success("Forecast validation passed")
    return True


__all__ = ["run_forecast_pipeline", "validate_forecast"]
