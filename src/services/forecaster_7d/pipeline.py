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
from forex_core.mlops import DataDriftDetector, DriftReport, PredictionTracker
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
        # Step 0: Initialize prediction tracker and update actuals
        logger.info("Initializing prediction tracker...")
        tracker = PredictionTracker()
        updated_count = tracker.update_actuals(lookback_days=180)
        logger.info(f"Updated {updated_count} predictions with actual values")

        # Step 1: Load data
        logger.info("Loading data from providers...")
        loader = DataLoader(settings)
        bundle: DataBundle = loader.load()
        logger.info(
            f"Data loaded: {len(bundle.indicators)} indicators, "
            f"{len(bundle.sources)} sources"
        )

        # Step 1.5: Run drift detection
        logger.info("Running drift detection on USD/CLP series...")
        drift_report = _detect_drift(settings, bundle)
        _log_drift_results(drift_report)

        # Step 2: Generate forecast
        logger.info(f"Generating {service_config.projection_days}-day forecast...")
        forecast, artifacts = _generate_forecast(settings, service_config, bundle)
        logger.info(
            f"Forecast generated: {len(forecast.series)} points, "
            f"final mean: {forecast.series[-1].mean:.2f}"
        )

        # Step 2.5: Log predictions for tracking
        logger.info("Logging predictions to tracker...")
        _log_predictions(tracker, start_time, forecast, service_config.horizon_code)

        # Step 2.6: Get recent performance metrics
        perf = tracker.get_recent_performance(horizon=service_config.horizon_code, days=60)
        _log_performance_metrics(perf, service_config.horizon_code)

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
            _send_email(settings, report_path, bundle, forecast, service_config)
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
    """
    from forex_core.reporting.charting import ChartGenerator

    generator = ChartGenerator(settings)
    return generator.generate(bundle, forecast, horizon=service_config.horizon)


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
    """
    from forex_core.reporting.builder import ReportBuilder

    builder = ReportBuilder(settings)

    # Convert EnsembleArtifacts to dict format expected by builder
    artifacts_dict = {
        "weights": artifacts.weights if hasattr(artifacts, "weights") else {},
        "models": artifacts.models if hasattr(artifacts, "models") else {},
    }

    return builder.build(
        bundle=bundle,
        forecast=forecast,
        artifacts=artifacts_dict,
        charts=chart_paths,
        horizon=service_config.horizon,
    )


def _send_email(
    settings,
    report_path: Path,
    bundle: DataBundle,
    forecast: ForecastPackage,
    service_config,
) -> None:
    """
    Send email notification with report attached, including executive summary.

    Args:
        settings: System settings with email configuration
        report_path: Path to generated PDF report
        bundle: DataBundle with market data
        forecast: ForecastPackage with forecast results
        service_config: Service configuration with horizon info
    """
    from forex_core.notifications.email import EmailSender

    sender = EmailSender(settings)
    sender.send(
        report_path=report_path,
        bundle=bundle,
        forecast=forecast.result,
        horizon=service_config.horizon_code,
    )


def _detect_drift(settings, bundle: DataBundle) -> Optional[DriftReport]:
    """
    Detect data drift in USD/CLP series.

    Args:
        settings: System settings.
        bundle: DataBundle with USD/CLP series.

    Returns:
        DriftReport if drift detection succeeds, None otherwise.
    """
    try:
        detector = DataDriftDetector(
            baseline_window=settings.drift_baseline_window,
            test_window=settings.drift_test_window,
            alpha=settings.drift_alpha
        )
        return detector.generate_drift_report(bundle.usdclp_series)
    except Exception as e:
        logger.warning(f"Drift detection failed: {e}")
        return None


def _log_drift_results(drift_report: Optional[DriftReport]) -> None:
    """
    Log drift detection results.

    Args:
        drift_report: DriftReport from detector.
    """
    if drift_report is None:
        logger.info("Drift detection: skipped")
        return

    logger.info(f"Drift detection: severity={drift_report.severity}")
    if hasattr(drift_report, "details"):
        logger.debug(f"Drift details: {drift_report.details}")


def _log_predictions(
    tracker: PredictionTracker,
    forecast_date: datetime,
    forecast: ForecastPackage,
    horizon: str,
) -> None:
    """
    Log all forecast points to the prediction tracker.

    Args:
        tracker: PredictionTracker instance.
        forecast_date: When this forecast was generated.
        forecast: ForecastPackage with predictions to log.
        horizon: Forecast horizon code ("7d", "15d", "30d", "90d").
    """
    try:
        for point in forecast.series:
            tracker.log_prediction(
                forecast_date=forecast_date,
                horizon=horizon,
                target_date=point.date,
                predicted_mean=point.mean,
                ci95_low=point.ci95_low,
                ci95_high=point.ci95_high,
            )
        logger.success(f"Logged {len(forecast.series)} predictions to tracker")
    except Exception as e:
        logger.error(f"Failed to log predictions: {e}")


def _log_performance_metrics(perf: dict, horizon: str) -> None:
    """
    Log out-of-sample performance metrics to logger.

    Args:
        perf: Performance metrics dictionary from tracker.
        horizon: Forecast horizon for context.
    """
    if perf["n_predictions"] == 0:
        logger.info(
            f"No out-of-sample performance data yet for {horizon} "
            f"({perf['n_total']} predictions pending)"
        )
        return

    logger.info(f"=== Out-of-Sample Performance ({horizon}, last 60 days) ===")
    logger.info(f"  Sample size: {perf['n_predictions']}/{perf['n_total']} predictions")

    if perf["rmse"] is not None:
        logger.info(f"  RMSE: {perf['rmse']:.2f} CLP")
    if perf["mae"] is not None:
        logger.info(f"  MAE: {perf['mae']:.2f} CLP")
    if perf["mape"] is not None:
        logger.info(f"  MAPE: {perf['mape']:.2%}")
    if perf["ci95_coverage"] is not None:
        logger.info(f"  CI95 Coverage: {perf['ci95_coverage']:.1%}")
    if perf["directional_accuracy"] is not None:
        logger.info(f"  Directional Accuracy: {perf['directional_accuracy']:.1%}")


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
            for v in [point.mean, point.ci95_low, point.ci95_high]
        ):
            logger.error(f"NaN value at forecast point {i}")
            return False

        # Check for positive values
        if point.mean <= 0:
            logger.error(f"Non-positive mean at forecast point {i}: {point.mean}")
            return False

        # Check interval validity
        if not (point.ci95_low <= point.mean <= point.ci95_high):
            logger.error(
                f"Invalid interval at point {i}: "
                f"ci95_low={point.ci95_low}, mean={point.mean}, ci95_high={point.ci95_high}"
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
