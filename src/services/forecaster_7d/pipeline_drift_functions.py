"""
Helper functions for drift detection integration in forecast pipelines.

These functions should be added to the pipeline.py file to enable drift detection.
"""

from datetime import datetime

from forex_core.data import DataBundle
from forex_core.data.models import ForecastPackage
from forex_core.mlops import DataDriftDetector, DriftReport
from forex_core.mlops.monitoring import DriftSeverity
from forex_core.utils.logging import logger


def _detect_drift(settings, bundle: DataBundle) -> DriftReport:
    """
    Run drift detection on USD/CLP series.

    Args:
        settings: System settings with drift detection configuration.
        bundle: DataBundle with historical USD/CLP data.

    Returns:
        DriftReport with comprehensive drift analysis.
    """
    detector = DataDriftDetector(
        baseline_window=settings.drift_baseline_window,
        test_window=settings.drift_test_window,
        alpha=settings.drift_alpha,
    )

    return detector.generate_drift_report(bundle.usdclp_series)


def _log_drift_results(drift_report: DriftReport) -> None:
    """
    Log drift detection results with appropriate severity level.

    Args:
        drift_report: Drift detection report to log.
    """
    if not drift_report.drift_detected:
        logger.info("No significant drift detected in USD/CLP data")
        logger.info(f"Baseline mean: {drift_report.baseline_mean:.2f} CLP")
        logger.info(f"Recent mean: {drift_report.recent_mean:.2f} CLP")
        return

    # Log based on severity
    if drift_report.severity == DriftSeverity.HIGH:
        logger.error(f"HIGH SEVERITY DRIFT DETECTED!")
    elif drift_report.severity == DriftSeverity.MEDIUM:
        logger.warning(f"MEDIUM SEVERITY DRIFT DETECTED")
    elif drift_report.severity == DriftSeverity.LOW:
        logger.warning(f"LOW SEVERITY DRIFT DETECTED")

    # Log statistics
    logger.info(
        f"Drift Statistics: "
        f"baseline_mean={drift_report.baseline_mean:.2f}, "
        f"recent_mean={drift_report.recent_mean:.2f}, "
        f"baseline_std={drift_report.baseline_std:.2f}, "
        f"recent_std={drift_report.recent_std:.2f}"
    )

    # Log failed tests
    failed_tests = [
        name for name, result in drift_report.tests.items()
        if result.drift_detected
    ]
    if failed_tests:
        logger.warning(f"Failed tests: {', '.join(failed_tests)}")

    # Log recommendation
    logger.info(f"Recommendation: {drift_report.recommendation}")


# Update _build_report signature to:
def _build_report_with_drift(
    settings,
    service_config,
    bundle,
    forecast,
    artifacts,
    chart_paths,
    drift_report: DriftReport,
):
    """
    Build PDF report with forecast results and drift information.

    This should replace the existing _build_report function.
    """
    from forex_core.reporting.builder import ReportBuilder

    builder = ReportBuilder(settings)

    # Convert EnsembleArtifacts to dict format expected by builder
    artifacts_dict = {
        "weights": artifacts.weights if hasattr(artifacts, "weights") else {},
        "models": artifacts.models if hasattr(artifacts, "models") else {},
        "drift_report": drift_report,  # Add drift report to artifacts
    }

    return builder.build(
        bundle=bundle,
        forecast=forecast,
        artifacts=artifacts_dict,
        charts=chart_paths,
        horizon=service_config.horizon,
    )


# Update _send_email signature to:
def _send_email_with_drift(
    settings,
    report_path,
    bundle,
    forecast,
    service_config,
    drift_report: DriftReport,
):
    """
    Send email notification with report attached, including drift alert if severe.

    This should replace the existing _send_email function.
    """
    from forex_core.notifications.email import EmailSender

    sender = EmailSender(settings)

    # Check if drift alert should be included
    alert_threshold = settings.drift_alert_threshold.lower()
    severity_levels = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    drift_alert = None
    if drift_report.drift_detected:
        current_severity = severity_levels.get(drift_report.severity.value, 0)
        threshold_severity = severity_levels.get(alert_threshold, 2)

        if current_severity >= threshold_severity:
            drift_alert = {
                "severity": drift_report.severity.value,
                "recommendation": drift_report.recommendation,
                "tests_failed": sum(
                    1 for test in drift_report.tests.values()
                    if test.drift_detected
                ),
            }

    sender.send(
        report_path=report_path,
        bundle=bundle,
        forecast=forecast.result,
        horizon=service_config.horizon_code,
        drift_alert=drift_alert,
    )
