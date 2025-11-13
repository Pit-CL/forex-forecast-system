"""
Data drift detection and monitoring for forex forecasting system.

This module provides statistical tests to detect when the underlying data
distribution changes, indicating that models may need retraining. It implements
multiple statistical tests to identify different types of drift:
- Distribution drift (Kolmogorov-Smirnov test)
- Mean shift (T-test)
- Variance change (Levene test)
- Autocorrelation change (Ljung-Box test)

The system compares a baseline window (historical data) against a recent window
to detect statistically significant changes that could affect model performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats


class DriftSeverity(str, Enum):
    """Severity levels for detected drift."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DriftTestResult:
    """
    Result of a single statistical drift test.

    Attributes:
        test_name: Name of the statistical test performed.
        statistic: Test statistic value.
        p_value: P-value from the test.
        drift_detected: Whether drift was detected at configured alpha.
        description: Human-readable description of the test result.
    """

    test_name: str
    statistic: float
    p_value: float
    drift_detected: bool
    description: str

    @property
    def is_significant(self) -> bool:
        """Check if this test detected significant drift."""
        return self.drift_detected


@dataclass
class DriftReport:
    """
    Complete drift detection report with all test results.

    Attributes:
        drift_detected: Overall drift detection flag (True if ANY test detected drift).
        severity: Severity level based on number and type of tests that failed.
        p_value: Minimum p-value across all tests (most significant).
        statistic: KS test statistic (primary drift indicator).
        baseline_mean: Mean of baseline window.
        recent_mean: Mean of recent window.
        baseline_std: Standard deviation of baseline window.
        recent_std: Standard deviation of recent window.
        baseline_size: Number of observations in baseline window.
        recent_size: Number of observations in recent window.
        tests: Dictionary of individual test results.
        recommendation: Action recommendation based on severity.
        timestamp: When the drift detection was performed.
    """

    drift_detected: bool
    severity: DriftSeverity
    p_value: float
    statistic: float
    baseline_mean: float
    recent_mean: float
    baseline_std: float
    recent_std: float
    baseline_size: int
    recent_size: int
    tests: Dict[str, DriftTestResult]
    recommendation: str
    timestamp: datetime

    def has_significant_drift(self) -> bool:
        """
        Check if there is significant drift requiring attention.

        Returns:
            True if drift detected with MEDIUM or HIGH severity.
        """
        return self.drift_detected and self.severity in [
            DriftSeverity.MEDIUM,
            DriftSeverity.HIGH,
        ]


class DataDriftDetector:
    """
    Statistical drift detector for time series data.

    Monitors USD/CLP exchange rate series for distributional changes that
    may require model recalibration. Implements multiple statistical tests
    to provide robust drift detection.

    Args:
        baseline_window: Number of days for baseline comparison (default: 90).
        test_window: Number of days for recent data window (default: 30).
        alpha: Significance level for statistical tests (default: 0.05).

    Example:
        >>> detector = DataDriftDetector(
        ...     baseline_window=90,
        ...     test_window=30,
        ...     alpha=0.05
        ... )
        >>> report = detector.generate_drift_report(usdclp_series)
        >>> if report.drift_detected:
        ...     print(f"Drift detected! Severity: {report.severity}")
        ...     print(f"Recommendation: {report.recommendation}")
    """

    def __init__(
        self,
        baseline_window: int = 90,
        test_window: int = 30,
        alpha: float = 0.05,
    ):
        """
        Initialize drift detector with window sizes and significance level.

        Args:
            baseline_window: Historical window size in days for baseline.
            test_window: Recent window size in days for comparison.
            alpha: Significance level for hypothesis tests (typ. 0.05).
        """
        self.baseline_window = baseline_window
        self.test_window = test_window
        self.alpha = alpha

        logger.info(
            f"DataDriftDetector initialized: "
            f"baseline={baseline_window}d, test={test_window}d, alpha={alpha}"
        )

    def detect_drift(
        self,
        series: pd.Series,
    ) -> Dict[str, any]:
        """
        Detect distribution drift using Kolmogorov-Smirnov test.

        The KS test is a non-parametric test that compares the empirical
        cumulative distribution functions of two samples. It's sensitive to
        changes in location, scale, and shape of the distribution.

        Args:
            series: Time series data (indexed by date).

        Returns:
            Dictionary with drift detection results:
                - drift_detected: bool
                - p_value: float
                - statistic: float (KS statistic)
                - severity: DriftSeverity

        Example:
            >>> result = detector.detect_drift(usdclp_series)
            >>> if result["drift_detected"]:
            ...     print(f"Distribution has changed (p={result['p_value']:.4f})")
        """
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            logger.warning("Insufficient data for drift detection")
            return {
                "drift_detected": False,
                "p_value": 1.0,
                "statistic": 0.0,
                "severity": DriftSeverity.NONE,
            }

        # Kolmogorov-Smirnov test for distribution difference
        ks_statistic, p_value = stats.ks_2samp(baseline, recent)
        drift_detected = p_value < self.alpha

        # Determine severity based on p-value and KS statistic
        severity = self._calculate_severity(p_value, ks_statistic)

        logger.debug(
            f"KS test: statistic={ks_statistic:.4f}, p_value={p_value:.4f}, "
            f"drift={drift_detected}, severity={severity}"
        )

        return {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "statistic": ks_statistic,
            "severity": severity,
        }

    def detect_volatility_regime_change(
        self,
        series: pd.Series,
        threshold_ratio: float = 1.5,
    ) -> bool:
        """
        Detect change in volatility regime.

        Compares standard deviations between baseline and recent windows.
        A regime change is detected if the volatility ratio exceeds the
        threshold in either direction (increased or decreased volatility).

        Args:
            series: Time series data (indexed by date).
            threshold_ratio: Ratio threshold for regime change (default: 1.5).
                If recent_std / baseline_std > threshold_ratio or < 1/threshold_ratio,
                a regime change is detected.

        Returns:
            True if volatility regime has changed significantly.

        Example:
            >>> if detector.detect_volatility_regime_change(series):
            ...     print("Volatility regime has changed - consider recalibration")
        """
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            return False

        baseline_std = baseline.std()
        recent_std = recent.std()

        if baseline_std == 0:
            logger.warning("Baseline standard deviation is zero")
            return False

        volatility_ratio = recent_std / baseline_std
        regime_change = (
            volatility_ratio > threshold_ratio or volatility_ratio < 1.0 / threshold_ratio
        )

        if regime_change:
            direction = "increased" if volatility_ratio > 1 else "decreased"
            logger.warning(
                f"Volatility regime change detected: {direction} "
                f"(ratio={volatility_ratio:.2f})"
            )

        return regime_change

    def detect_mean_shift(self, series: pd.Series) -> DriftTestResult:
        """
        Detect shift in mean level using Welch's t-test.

        The t-test compares the means of two independent samples to determine
        if they come from populations with equal means. Welch's version doesn't
        assume equal variances, making it more robust.

        Args:
            series: Time series data (indexed by date).

        Returns:
            DriftTestResult with t-test results and interpretation.

        Example:
            >>> result = detector.detect_mean_shift(usdclp_series)
            >>> if result.drift_detected:
            ...     print(f"Mean has shifted: {result.description}")
        """
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            return DriftTestResult(
                test_name="T-test (Mean Shift)",
                statistic=0.0,
                p_value=1.0,
                drift_detected=False,
                description="Insufficient data for t-test",
            )

        # Welch's t-test (doesn't assume equal variances)
        t_statistic, p_value = stats.ttest_ind(
            baseline, recent, equal_var=False
        )

        drift_detected = p_value < self.alpha

        mean_diff = recent.mean() - baseline.mean()
        direction = "increased" if mean_diff > 0 else "decreased"
        description = (
            f"Mean {direction} from {baseline.mean():.2f} to {recent.mean():.2f} "
            f"(diff={abs(mean_diff):.2f}, p={p_value:.4f})"
        )

        return DriftTestResult(
            test_name="T-test (Mean Shift)",
            statistic=float(t_statistic),
            p_value=float(p_value),
            drift_detected=drift_detected,
            description=description,
        )

    def detect_variance_change(self, series: pd.Series) -> DriftTestResult:
        """
        Detect change in variance using Levene's test.

        Levene's test is robust to departures from normality and tests
        whether samples have equal variances. It's more reliable than
        the F-test when the normality assumption is violated.

        Args:
            series: Time series data (indexed by date).

        Returns:
            DriftTestResult with Levene test results.

        Example:
            >>> result = detector.detect_variance_change(usdclp_series)
            >>> if result.drift_detected:
            ...     print("Variance has changed significantly")
        """
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            return DriftTestResult(
                test_name="Levene Test (Variance Change)",
                statistic=0.0,
                p_value=1.0,
                drift_detected=False,
                description="Insufficient data for Levene test",
            )

        # Levene's test for equal variances
        levene_statistic, p_value = stats.levene(baseline, recent)
        drift_detected = p_value < self.alpha

        var_ratio = recent.var() / baseline.var() if baseline.var() > 0 else np.inf
        description = (
            f"Variance ratio: {var_ratio:.2f} "
            f"(baseline={baseline.std():.2f}, recent={recent.std():.2f}, "
            f"p={p_value:.4f})"
        )

        return DriftTestResult(
            test_name="Levene Test (Variance Change)",
            statistic=float(levene_statistic),
            p_value=float(p_value),
            drift_detected=drift_detected,
            description=description,
        )

    def detect_autocorrelation_change(
        self,
        series: pd.Series,
        lags: int = 10,
    ) -> DriftTestResult:
        """
        Detect change in autocorrelation structure using Ljung-Box test.

        The Ljung-Box test examines whether residuals exhibit autocorrelation.
        Changes in autocorrelation patterns may indicate structural breaks
        in the time series dynamics.

        Args:
            series: Time series data (indexed by date).
            lags: Number of lags to test (default: 10).

        Returns:
            DriftTestResult with Ljung-Box test results.

        Example:
            >>> result = detector.detect_autocorrelation_change(usdclp_series)
            >>> if result.drift_detected:
            ...     print("Autocorrelation structure has changed")
        """
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            return DriftTestResult(
                test_name="Ljung-Box Test (Autocorrelation)",
                statistic=0.0,
                p_value=1.0,
                drift_detected=False,
                description="Insufficient data for Ljung-Box test",
            )

        # Ensure we have enough data for the specified lags
        min_length = min(len(baseline), len(recent))
        if min_length < lags + 1:
            lags = max(1, min_length - 1)

        try:
            # Calculate first-order differences to remove trend
            baseline_diff = baseline.diff().dropna()
            recent_diff = recent.diff().dropna()

            # Ljung-Box test on differenced series
            from statsmodels.stats.diagnostic import acorr_ljungbox

            lb_baseline = acorr_ljungbox(baseline_diff, lags=lags, return_df=False)
            lb_recent = acorr_ljungbox(recent_diff, lags=lags, return_df=False)

            # Use the minimum p-value from either test
            p_value_baseline = float(lb_baseline[1].min())
            p_value_recent = float(lb_recent[1].min())

            # Detect drift if autocorrelation is present in one but not the other
            baseline_has_autocorr = p_value_baseline < self.alpha
            recent_has_autocorr = p_value_recent < self.alpha

            drift_detected = baseline_has_autocorr != recent_has_autocorr

            statistic = float(
                max(lb_baseline[0].max(), lb_recent[0].max())
            )
            p_value = min(p_value_baseline, p_value_recent)

            description = (
                f"Autocorrelation change: baseline_p={p_value_baseline:.4f}, "
                f"recent_p={p_value_recent:.4f}"
            )

            return DriftTestResult(
                test_name="Ljung-Box Test (Autocorrelation)",
                statistic=statistic,
                p_value=p_value,
                drift_detected=drift_detected,
                description=description,
            )

        except Exception as e:
            logger.warning(f"Ljung-Box test failed: {e}")
            return DriftTestResult(
                test_name="Ljung-Box Test (Autocorrelation)",
                statistic=0.0,
                p_value=1.0,
                drift_detected=False,
                description=f"Test failed: {str(e)}",
            )

    def generate_drift_report(self, series: pd.Series) -> DriftReport:
        """
        Generate comprehensive drift detection report with all tests.

        Runs all available statistical tests and aggregates results into
        a single report with overall drift assessment and recommendations.

        Args:
            series: Time series data (indexed by date).

        Returns:
            DriftReport with complete analysis and recommendations.

        Example:
            >>> report = detector.generate_drift_report(usdclp_series)
            >>> print(f"Drift: {report.drift_detected}")
            >>> print(f"Severity: {report.severity}")
            >>> print(f"Recommendation: {report.recommendation}")
            >>> for test_name, result in report.tests.items():
            ...     print(f"{test_name}: {result.description}")
        """
        logger.info("Generating comprehensive drift report")

        # Get baseline and recent windows for summary stats
        baseline, recent = self._split_windows(series)

        if baseline is None or recent is None:
            logger.warning("Insufficient data for drift report")
            return self._create_empty_report()

        # Run all drift tests
        ks_result = self.detect_drift(series)
        mean_shift = self.detect_mean_shift(series)
        variance_change = self.detect_variance_change(series)
        autocorr_change = self.detect_autocorrelation_change(series)
        volatility_regime = self.detect_volatility_regime_change(series)

        # Aggregate results
        tests_dict = {
            "ks_test": DriftTestResult(
                test_name="Kolmogorov-Smirnov Test",
                statistic=ks_result["statistic"],
                p_value=ks_result["p_value"],
                drift_detected=ks_result["drift_detected"],
                description=f"Distribution change (p={ks_result['p_value']:.4f})",
            ),
            "t_test": mean_shift,
            "levene_test": variance_change,
            "ljungbox_test": autocorr_change,
        }

        # Overall drift detection (True if ANY test detected drift)
        drift_detected = (
            any(test.drift_detected for test in tests_dict.values())
            or volatility_regime
        )

        # Calculate overall severity
        severity = self._aggregate_severity(tests_dict, volatility_regime)

        # Find minimum p-value (most significant result)
        p_values = [test.p_value for test in tests_dict.values() if test.p_value > 0]
        min_p_value = min(p_values) if p_values else 1.0

        # Generate recommendation
        recommendation = self._generate_recommendation(severity, tests_dict)

        report = DriftReport(
            drift_detected=drift_detected,
            severity=severity,
            p_value=min_p_value,
            statistic=ks_result["statistic"],
            baseline_mean=float(baseline.mean()),
            recent_mean=float(recent.mean()),
            baseline_std=float(baseline.std()),
            recent_std=float(recent.std()),
            baseline_size=len(baseline),
            recent_size=len(recent),
            tests=tests_dict,
            recommendation=recommendation,
            timestamp=datetime.now(),
        )

        # Log summary
        if drift_detected:
            logger.warning(
                f"Drift detected! Severity: {severity}, "
                f"Tests failed: {sum(t.drift_detected for t in tests_dict.values())}/4"
            )
        else:
            logger.info("No significant drift detected")

        return report

    def _split_windows(
        self,
        series: pd.Series,
    ) -> tuple[Optional[pd.Series], Optional[pd.Series]]:
        """
        Split series into baseline and recent windows.

        Args:
            series: Time series data.

        Returns:
            Tuple of (baseline_window, recent_window). Returns (None, None)
            if insufficient data is available.
        """
        if len(series) < self.baseline_window + self.test_window:
            logger.warning(
                f"Insufficient data: need {self.baseline_window + self.test_window} "
                f"points, have {len(series)}"
            )
            return None, None

        # Get the most recent data
        recent = series.iloc[-self.test_window :]

        # Get baseline window (ending before recent window)
        baseline = series.iloc[
            -(self.baseline_window + self.test_window) : -self.test_window
        ]

        return baseline, recent

    def _calculate_severity(
        self,
        p_value: float,
        ks_statistic: float,
    ) -> DriftSeverity:
        """
        Calculate drift severity based on p-value and KS statistic.

        Severity levels:
        - HIGH: p < 0.01 and KS > 0.3 (strong evidence, large effect)
        - MEDIUM: p < 0.05 and KS > 0.2 (moderate evidence)
        - LOW: p < 0.05 (weak evidence or small effect)
        - NONE: p >= 0.05 (no significant drift)

        Args:
            p_value: P-value from statistical test.
            ks_statistic: Kolmogorov-Smirnov statistic.

        Returns:
            DriftSeverity level.
        """
        if p_value >= self.alpha:
            return DriftSeverity.NONE

        # Significant drift detected, classify severity
        if p_value < 0.01 and ks_statistic > 0.3:
            return DriftSeverity.HIGH
        elif p_value < 0.05 and ks_statistic > 0.2:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.LOW

    def _aggregate_severity(
        self,
        tests: Dict[str, DriftTestResult],
        volatility_regime: bool,
    ) -> DriftSeverity:
        """
        Aggregate severity across multiple tests.

        Args:
            tests: Dictionary of test results.
            volatility_regime: Whether volatility regime changed.

        Returns:
            Overall DriftSeverity level.
        """
        failed_tests = sum(test.drift_detected for test in tests.values())

        if volatility_regime:
            failed_tests += 1

        min_p_value = min(
            (test.p_value for test in tests.values() if test.p_value > 0),
            default=1.0,
        )

        # Severe drift: multiple tests failed or very low p-value
        if failed_tests >= 3 or min_p_value < 0.001:
            return DriftSeverity.HIGH
        elif failed_tests == 2 or min_p_value < 0.01:
            return DriftSeverity.MEDIUM
        elif failed_tests == 1:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _generate_recommendation(
        self,
        severity: DriftSeverity,
        tests: Dict[str, DriftTestResult],
    ) -> str:
        """
        Generate action recommendation based on drift severity.

        Args:
            severity: Overall drift severity.
            tests: Dictionary of test results.

        Returns:
            Human-readable recommendation string.
        """
        if severity == DriftSeverity.HIGH:
            return (
                "CRITICAL: Significant data drift detected. "
                "Immediate model retraining strongly recommended. "
                "Current forecasts may be unreliable."
            )
        elif severity == DriftSeverity.MEDIUM:
            return (
                "WARNING: Moderate data drift detected. "
                "Consider retraining models soon to maintain forecast accuracy. "
                "Monitor performance closely."
            )
        elif severity == DriftSeverity.LOW:
            return (
                "ADVISORY: Minor drift detected in data distribution. "
                "Continue monitoring. Retraining may be beneficial but not urgent."
            )
        else:
            return (
                "OK: No significant drift detected. "
                "Current models are likely still valid for forecasting."
            )

    def _create_empty_report(self) -> DriftReport:
        """
        Create an empty report when insufficient data is available.

        Returns:
            DriftReport with all tests marked as insufficient data.
        """
        return DriftReport(
            drift_detected=False,
            severity=DriftSeverity.NONE,
            p_value=1.0,
            statistic=0.0,
            baseline_mean=0.0,
            recent_mean=0.0,
            baseline_std=0.0,
            recent_std=0.0,
            baseline_size=0,
            recent_size=0,
            tests={},
            recommendation="Insufficient data for drift detection",
            timestamp=datetime.now(),
        )


__all__ = [
    "DataDriftDetector",
    "DriftReport",
    "DriftTestResult",
    "DriftSeverity",
]
