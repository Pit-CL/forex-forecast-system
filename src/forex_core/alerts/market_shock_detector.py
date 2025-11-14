"""
Market Shock Detector for USD/CLP Autonomous Forecasting System.

Detects market events and anomalies that could significantly impact USD/CLP forecasts.
This module implements the alert triggers defined in Phase 2 of the implementation plan.

Detection Categories:
    1. Sudden Trend Changes in USD/CLP
    2. Volatility Spikes
    3. Copper Price Shocks (Chile's main export)
    4. DXY Extreme Movements
    5. VIX Fear Spikes
    6. Chilean Political Events (TPM changes)

Each detection returns Alert objects with severity classification (INFO, WARNING, CRITICAL)
and relevant metrics for email generation.

Example:
    >>> import pandas as pd
    >>> from market_shock_detector import MarketShockDetector
    >>>
    >>> # Prepare data with required columns
    >>> data = pd.DataFrame({
    ...     'date': pd.date_range('2025-01-01', periods=60),
    ...     'usdclp': [...],
    ...     'copper_price': [...],
    ...     'dxy': [...],
    ...     'vix': [...],
    ...     'tpm': [...]
    ... })
    >>>
    >>> detector = MarketShockDetector()
    >>> alerts = detector.detect_all(data)
    >>>
    >>> for alert in alerts:
    ...     print(f"{alert.severity}: {alert.message}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger


class AlertType(str, Enum):
    """Types of market shock alerts."""

    TREND_REVERSAL = "TREND_REVERSAL"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    COPPER_SHOCK = "COPPER_SHOCK"
    DXY_EXTREME = "DXY_EXTREME"
    VIX_SPIKE = "VIX_SPIKE"
    TPM_SURPRISE = "TPM_SURPRISE"


class AlertSeverity(str, Enum):
    """Alert severity levels for prioritization and notification logic."""

    INFO = "INFO"  # Single indicator at threshold, informational only
    WARNING = "WARNING"  # Moderate movement, attention recommended
    CRITICAL = "CRITICAL"  # Extreme movement, immediate action required


@dataclass
class Alert:
    """
    Represents a detected market shock event.

    Attributes:
        alert_type: Category of the alert
        severity: Severity level for prioritization
        timestamp: When the alert was triggered
        message: Human-readable alert description
        metrics: Relevant numerical metrics
        recommendation: Optional action recommendation
    """

    alert_type: AlertType
    severity: AlertSeverity
    timestamp: datetime
    message: str
    metrics: Dict[str, float] = field(default_factory=dict)
    recommendation: Optional[str] = None

    def __str__(self) -> str:
        """Return human-readable alert summary."""
        return f"[{self.severity.value}] {self.alert_type.value}: {self.message}"

    def to_dict(self) -> Dict:
        """Convert alert to dictionary for serialization."""
        return {
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "metrics": self.metrics,
            "recommendation": self.recommendation,
        }


class MarketShockDetector:
    """
    Detects market shocks and anomalies affecting USD/CLP forecasts.

    This class implements the alert triggers defined in the implementation plan,
    with configurable thresholds to tune sensitivity and reduce false positives.

    Attributes:
        usdclp_daily_threshold: % change for single-day USD/CLP alert (default: 2.0%)
        usdclp_swing_threshold: % swing for 3-day trend reversal (default: 3.0%)
        volatility_multiplier: Multiplier vs 30-day average (default: 1.5x)
        intraday_range_threshold: Intraday range % threshold (default: 3.0%)
        copper_daily_threshold: % change for copper daily alert (default: 5.0%)
        copper_weekly_threshold: % decline for copper weekly alert (default: 10.0%)
        dxy_high_threshold: DXY level for strong dollar alert (default: 105)
        dxy_low_threshold: DXY level for weak dollar alert (default: 95)
        dxy_daily_threshold: Daily DXY % change threshold (default: 1.0%)
        vix_fear_threshold: VIX level for fear alert (default: 30)
        vix_change_threshold: VIX % change threshold (default: 20%)
        tpm_surprise_threshold: TPM unexpected change in basis points (default: 50bp = 0.5%)
    """

    def __init__(
        self,
        # USD/CLP thresholds
        usdclp_daily_threshold: float = 2.0,
        usdclp_swing_threshold: float = 3.0,
        # Volatility thresholds
        volatility_multiplier: float = 1.5,
        intraday_range_threshold: float = 3.0,
        # Copper thresholds
        copper_daily_threshold: float = 5.0,
        copper_weekly_threshold: float = 10.0,
        # DXY thresholds
        dxy_high_threshold: float = 105.0,
        dxy_low_threshold: float = 95.0,
        dxy_daily_threshold: float = 1.0,
        # VIX thresholds
        vix_fear_threshold: float = 30.0,
        vix_change_threshold: float = 20.0,
        # TPM thresholds
        tpm_surprise_threshold: float = 0.5,
    ):
        """
        Initialize market shock detector with configurable thresholds.

        All percentage thresholds are in percentage points (e.g., 2.0 = 2%).
        """
        # USD/CLP
        self.usdclp_daily_threshold = usdclp_daily_threshold
        self.usdclp_swing_threshold = usdclp_swing_threshold

        # Volatility
        self.volatility_multiplier = volatility_multiplier
        self.intraday_range_threshold = intraday_range_threshold

        # Copper
        self.copper_daily_threshold = copper_daily_threshold
        self.copper_weekly_threshold = copper_weekly_threshold

        # DXY
        self.dxy_high_threshold = dxy_high_threshold
        self.dxy_low_threshold = dxy_low_threshold
        self.dxy_daily_threshold = dxy_daily_threshold

        # VIX
        self.vix_fear_threshold = vix_fear_threshold
        self.vix_change_threshold = vix_change_threshold

        # TPM
        self.tpm_surprise_threshold = tpm_surprise_threshold

        logger.info("MarketShockDetector initialized with custom thresholds")

    def detect_all(self, data: pd.DataFrame) -> List[Alert]:
        """
        Run all detection algorithms on provided market data.

        Args:
            data: DataFrame with columns:
                - date: pd.Timestamp or datetime
                - usdclp: USD/CLP exchange rate
                - copper_price: Copper price ($/lb or similar)
                - dxy: US Dollar Index
                - vix: CBOE Volatility Index
                - tpm: Chilean policy rate (%)
                Optional columns for enhanced detection:
                - usdclp_high: Intraday high
                - usdclp_low: Intraday low

        Returns:
            List of Alert objects, sorted by severity (CRITICAL first)

        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        self._validate_data(data)

        alerts: List[Alert] = []

        # 1. USD/CLP Trend Changes
        alerts.extend(self._detect_trend_changes(data))

        # 2. Volatility Spikes
        alerts.extend(self._detect_volatility_spikes(data))

        # 3. Copper Shocks
        alerts.extend(self._detect_copper_shocks(data))

        # 4. DXY Extremes
        alerts.extend(self._detect_dxy_extremes(data))

        # 5. VIX Spikes
        alerts.extend(self._detect_vix_spikes(data))

        # 6. TPM Surprises
        alerts.extend(self._detect_tpm_surprises(data))

        # Sort by severity: CRITICAL > WARNING > INFO
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.INFO: 2,
        }
        alerts.sort(key=lambda a: severity_order[a.severity])

        logger.info(
            f"Detection complete: {len(alerts)} alerts "
            f"(CRITICAL: {sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)}, "
            f"WARNING: {sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)}, "
            f"INFO: {sum(1 for a in alerts if a.severity == AlertSeverity.INFO)})"
        )

        return alerts

    def _validate_data(self, data: pd.DataFrame) -> None:
        """
        Validate that data contains required columns and sufficient history.

        Args:
            data: Market data DataFrame

        Raises:
            ValueError: If validation fails
        """
        required_columns = ["date", "usdclp", "copper_price", "dxy", "vix", "tpm"]
        missing = [col for col in required_columns if col not in data.columns]

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}. "
                f"Required: {required_columns}"
            )

        if len(data) < 30:
            raise ValueError(
                f"Insufficient data: {len(data)} rows. Need at least 30 days of history."
            )

        # Check for NaN in critical recent data
        recent_data = data.tail(7)
        for col in ["usdclp", "copper_price", "dxy", "vix"]:
            if recent_data[col].isna().sum() > 0:
                logger.warning(f"Found NaN values in recent {col} data")

    def _detect_trend_changes(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect sudden trend changes in USD/CLP.

        Triggers:
            - Single-day change > threshold (default 2%)
            - 3-day trend reversal with swing > threshold (default 3%)

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for trend changes
        """
        alerts = []

        # Calculate daily returns
        usdclp = data["usdclp"].copy()
        daily_change = usdclp.pct_change() * 100  # Convert to percentage

        # 1. Single-day shock
        latest_change = daily_change.iloc[-1]
        if abs(latest_change) >= self.usdclp_daily_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if abs(latest_change) >= self.usdclp_daily_threshold * 2
                else AlertSeverity.WARNING
            )

            direction = "alza" if latest_change > 0 else "baja"
            current_rate = usdclp.iloc[-1]

            alerts.append(
                Alert(
                    alert_type=AlertType.TREND_REVERSAL,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Cambio diario significativo en USD/CLP: {direction} de {abs(latest_change):.2f}% a ${current_rate:.2f}",
                    metrics={
                        "daily_change_pct": latest_change,
                        "current_rate": current_rate,
                        "previous_rate": usdclp.iloc[-2],
                    },
                    recommendation="Revisar drivers del movimiento y actualizar expectativas de corto plazo"
                    if severity == AlertSeverity.CRITICAL
                    else None,
                )
            )

        # 2. 3-day trend reversal
        if len(data) >= 4:
            # Check if direction changed between day -3 and day 0
            three_day_window = usdclp.iloc[-4:]
            initial_value = three_day_window.iloc[0]
            final_value = three_day_window.iloc[-1]
            total_change = ((final_value - initial_value) / initial_value) * 100

            # Check for swing: prices went one direction then reversed
            max_value = three_day_window.max()
            min_value = three_day_window.min()
            swing = ((max_value - min_value) / min_value) * 100

            if swing >= self.usdclp_swing_threshold:
                # Determine reversal direction
                if three_day_window.idxmax() < three_day_window.idxmin():
                    reversal_type = "alza seguida de caída"
                else:
                    reversal_type = "caída seguida de alza"

                alerts.append(
                    Alert(
                        alert_type=AlertType.TREND_REVERSAL,
                        severity=AlertSeverity.WARNING,
                        timestamp=datetime.now(),
                        message=f"Reversión de tendencia detectada (3 días): {reversal_type} con swing de {swing:.2f}%",
                        metrics={
                            "swing_pct": swing,
                            "total_change_pct": total_change,
                            "max_rate": max_value,
                            "min_rate": min_value,
                            "current_rate": final_value,
                        },
                        recommendation="Monitorear confirmación de nueva tendencia",
                    )
                )

        return alerts

    def _detect_volatility_spikes(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect volatility spikes in USD/CLP.

        Triggers:
            - Daily volatility > multiplier * 30-day average (default 1.5x)
            - Intraday range > threshold (default 3%, requires high/low data)

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for volatility spikes
        """
        alerts = []

        # Calculate rolling volatility (30-day)
        if len(data) >= 30:
            returns = data["usdclp"].pct_change().dropna()

            # Recent 7-day volatility vs 30-day average
            recent_vol = returns.tail(7).std() * (252**0.5)  # Annualized
            historical_vol = returns.tail(30).std() * (252**0.5)

            if historical_vol > 0:
                vol_ratio = recent_vol / historical_vol

                if vol_ratio >= self.volatility_multiplier:
                    severity = (
                        AlertSeverity.CRITICAL
                        if vol_ratio >= self.volatility_multiplier * 1.5
                        else AlertSeverity.WARNING
                    )

                    alerts.append(
                        Alert(
                            alert_type=AlertType.VOLATILITY_SPIKE,
                            severity=severity,
                            timestamp=datetime.now(),
                            message=f"Volatilidad elevada: {vol_ratio:.1f}x el promedio de 30 días ({recent_vol:.1f}% anual vs {historical_vol:.1f}%)",
                            metrics={
                                "recent_volatility": recent_vol,
                                "historical_volatility": historical_vol,
                                "volatility_ratio": vol_ratio,
                            },
                            recommendation="Ampliar intervalos de confianza en forecasts"
                            if severity == AlertSeverity.CRITICAL
                            else None,
                        )
                    )

        # Intraday range check (if high/low data available)
        if "usdclp_high" in data.columns and "usdclp_low" in data.columns:
            latest_high = data["usdclp_high"].iloc[-1]
            latest_low = data["usdclp_low"].iloc[-1]
            latest_close = data["usdclp"].iloc[-1]

            if latest_low > 0:
                intraday_range = ((latest_high - latest_low) / latest_low) * 100

                if intraday_range >= self.intraday_range_threshold:
                    alerts.append(
                        Alert(
                            alert_type=AlertType.VOLATILITY_SPIKE,
                            severity=AlertSeverity.WARNING,
                            timestamp=datetime.now(),
                            message=f"Rango intradiario amplio: {intraday_range:.2f}% (${latest_low:.2f} - ${latest_high:.2f})",
                            metrics={
                                "intraday_range_pct": intraday_range,
                                "high": latest_high,
                                "low": latest_low,
                                "close": latest_close,
                            },
                        )
                    )

        return alerts

    def _detect_copper_shocks(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect copper price shocks (critical for Chilean economy).

        Triggers:
            - Daily change > threshold (default 5%)
            - Sustained weekly decline > threshold (default 10%)

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for copper shocks
        """
        alerts = []

        copper = data["copper_price"].dropna()
        if len(copper) < 2:
            return alerts

        # 1. Daily shock
        daily_change = copper.pct_change().iloc[-1] * 100

        if abs(daily_change) >= self.copper_daily_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if abs(daily_change) >= self.copper_daily_threshold * 1.5
                else AlertSeverity.WARNING
            )

            direction = "alza" if daily_change > 0 else "caída"
            current_price = copper.iloc[-1]

            alerts.append(
                Alert(
                    alert_type=AlertType.COPPER_SHOCK,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Shock en precio del cobre: {direction} de {abs(daily_change):.2f}% a ${current_price:.2f}/lb",
                    metrics={
                        "daily_change_pct": daily_change,
                        "current_price": current_price,
                        "previous_price": copper.iloc[-2],
                    },
                    recommendation="Evaluar impacto en balanza comercial chilena y presión sobre CLP",
                )
            )

        # 2. Sustained weekly decline
        if len(copper) >= 7:
            week_start = copper.iloc[-7]
            week_end = copper.iloc[-1]
            weekly_change = ((week_end - week_start) / week_start) * 100

            if weekly_change <= -self.copper_weekly_threshold:
                alerts.append(
                    Alert(
                        alert_type=AlertType.COPPER_SHOCK,
                        severity=AlertSeverity.WARNING,
                        timestamp=datetime.now(),
                        message=f"Caída sostenida del cobre (7 días): {abs(weekly_change):.2f}% (${week_start:.2f} → ${week_end:.2f})",
                        metrics={
                            "weekly_change_pct": weekly_change,
                            "week_start_price": week_start,
                            "week_end_price": week_end,
                        },
                        recommendation="Monitorear impacto acumulado en exportaciones chilenas",
                    )
                )

        return alerts

    def _detect_dxy_extremes(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect DXY (US Dollar Index) extreme movements.

        Triggers:
            - DXY > high threshold (default 105, strong dollar)
            - DXY < low threshold (default 95, weak dollar)
            - Daily DXY change > threshold (default 1%)

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for DXY extremes
        """
        alerts = []

        dxy = data["dxy"].dropna()
        if len(dxy) < 2:
            return alerts

        current_dxy = dxy.iloc[-1]
        previous_dxy = dxy.iloc[-2]
        daily_change = ((current_dxy - previous_dxy) / previous_dxy) * 100

        # 1. Extreme levels
        if current_dxy >= self.dxy_high_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if current_dxy >= self.dxy_high_threshold + 2
                else AlertSeverity.INFO
            )

            alerts.append(
                Alert(
                    alert_type=AlertType.DXY_EXTREME,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Dólar fuerte: DXY en {current_dxy:.2f} (umbral {self.dxy_high_threshold})",
                    metrics={
                        "current_dxy": current_dxy,
                        "threshold": self.dxy_high_threshold,
                        "distance_from_threshold": current_dxy - self.dxy_high_threshold,
                    },
                    recommendation="Presión alcista generalizada sobre USD, incluido USD/CLP"
                    if severity == AlertSeverity.CRITICAL
                    else None,
                )
            )

        elif current_dxy <= self.dxy_low_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if current_dxy <= self.dxy_low_threshold - 2
                else AlertSeverity.INFO
            )

            alerts.append(
                Alert(
                    alert_type=AlertType.DXY_EXTREME,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Dólar débil: DXY en {current_dxy:.2f} (umbral {self.dxy_low_threshold})",
                    metrics={
                        "current_dxy": current_dxy,
                        "threshold": self.dxy_low_threshold,
                        "distance_from_threshold": self.dxy_low_threshold - current_dxy,
                    },
                    recommendation="Presión bajista generalizada sobre USD, incluido USD/CLP"
                    if severity == AlertSeverity.CRITICAL
                    else None,
                )
            )

        # 2. Daily change
        if abs(daily_change) >= self.dxy_daily_threshold:
            severity = (
                AlertSeverity.WARNING
                if abs(daily_change) >= self.dxy_daily_threshold * 1.5
                else AlertSeverity.INFO
            )

            direction = "alza" if daily_change > 0 else "caída"

            alerts.append(
                Alert(
                    alert_type=AlertType.DXY_EXTREME,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Movimiento significativo en DXY: {direction} de {abs(daily_change):.2f}% a {current_dxy:.2f}",
                    metrics={
                        "daily_change_pct": daily_change,
                        "current_dxy": current_dxy,
                        "previous_dxy": previous_dxy,
                    },
                )
            )

        return alerts

    def _detect_vix_spikes(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect VIX (fear index) spikes indicating market stress.

        Triggers:
            - VIX > threshold (default 30, global stress)
            - VIX daily change > threshold (default +20%)

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for VIX spikes
        """
        alerts = []

        vix = data["vix"].dropna()
        if len(vix) < 2:
            return alerts

        current_vix = vix.iloc[-1]
        previous_vix = vix.iloc[-2]
        daily_change = ((current_vix - previous_vix) / previous_vix) * 100

        # 1. Absolute level
        if current_vix >= self.vix_fear_threshold:
            if current_vix >= 40:
                severity = AlertSeverity.CRITICAL
                stress_level = "extremo"
            elif current_vix >= 35:
                severity = AlertSeverity.WARNING
                stress_level = "alto"
            else:
                severity = AlertSeverity.INFO
                stress_level = "moderado"

            alerts.append(
                Alert(
                    alert_type=AlertType.VIX_SPIKE,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Estrés de mercado {stress_level}: VIX en {current_vix:.1f} (umbral {self.vix_fear_threshold})",
                    metrics={
                        "current_vix": current_vix,
                        "threshold": self.vix_fear_threshold,
                        "stress_level": stress_level,
                    },
                    recommendation="Flight to quality: aumentar aversión al riesgo en forecast de EM"
                    if severity == AlertSeverity.CRITICAL
                    else None,
                )
            )

        # 2. Daily spike
        if daily_change >= self.vix_change_threshold:
            severity = (
                AlertSeverity.WARNING
                if daily_change >= self.vix_change_threshold * 1.5
                else AlertSeverity.INFO
            )

            alerts.append(
                Alert(
                    alert_type=AlertType.VIX_SPIKE,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Spike en VIX: alza de {daily_change:.1f}% a {current_vix:.1f} (desde {previous_vix:.1f})",
                    metrics={
                        "daily_change_pct": daily_change,
                        "current_vix": current_vix,
                        "previous_vix": previous_vix,
                    },
                    recommendation="Evento de riesgo reciente: revisar noticias globales",
                )
            )

        return alerts

    def _detect_tpm_surprises(self, data: pd.DataFrame) -> List[Alert]:
        """
        Detect TPM (Chilean policy rate) surprise changes.

        Triggers:
            - TPM change >= surprise threshold (default 0.5% = 50bp)

        Note:
            This is a basic implementation. Production version should:
            - Integrate with BCCh meeting calendar
            - Compare actual vs market expectations
            - Track survey consensus

        Args:
            data: Market data DataFrame

        Returns:
            List of alerts for TPM surprises
        """
        alerts = []

        tpm = data["tpm"].dropna()
        if len(tpm) < 2:
            return alerts

        # Detect changes (TPM usually changes in 25bp or 50bp increments)
        tpm_diff = tpm.diff().dropna()
        recent_changes = tpm_diff.tail(5)  # Check last 5 observations

        # Find latest change
        latest_change = tpm_diff.iloc[-1]

        if abs(latest_change) >= self.tpm_surprise_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if abs(latest_change) >= 1.0
                else AlertSeverity.WARNING
            )

            direction = "alza" if latest_change > 0 else "baja"
            current_tpm = tpm.iloc[-1]
            previous_tpm = tpm.iloc[-2]

            # Determine if surprise (simplified logic)
            is_surprise = abs(latest_change) >= 0.75  # 75bp or more is unusual

            surprise_text = " (SORPRESA)" if is_surprise else ""

            alerts.append(
                Alert(
                    alert_type=AlertType.TPM_SURPRISE,
                    severity=severity,
                    timestamp=datetime.now(),
                    message=f"Cambio en TPM{surprise_text}: {direction} de {abs(latest_change):.2f}% a {current_tpm:.2f}% (desde {previous_tpm:.2f}%)",
                    metrics={
                        "tpm_change": latest_change,
                        "current_tpm": current_tpm,
                        "previous_tpm": previous_tpm,
                        "is_surprise": is_surprise,
                    },
                    recommendation="Re-calibrar expectativas de diferenciales de tasas USD/CLP"
                    if severity == AlertSeverity.CRITICAL
                    else None,
                )
            )

        return alerts

    def get_alert_summary(self, alerts: List[Alert]) -> str:
        """
        Generate human-readable summary of alerts for email subject/preview.

        Args:
            alerts: List of detected alerts

        Returns:
            Concise summary string (1-2 sentences)
        """
        if not alerts:
            return "Sin alertas de mercado detectadas"

        critical_count = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
        warning_count = sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)
        info_count = sum(1 for a in alerts if a.severity == AlertSeverity.INFO)

        if critical_count > 0:
            critical_alerts = [
                a for a in alerts if a.severity == AlertSeverity.CRITICAL
            ]
            types = ", ".join(
                set(a.alert_type.value.replace("_", " ") for a in critical_alerts[:2])
            )
            return f"CRÍTICO: {critical_count} alerta(s) - {types}"
        elif warning_count > 0:
            warning_alerts = [a for a in alerts if a.severity == AlertSeverity.WARNING]
            types = ", ".join(
                set(a.alert_type.value.replace("_", " ") for a in warning_alerts[:2])
            )
            return f"ADVERTENCIA: {warning_count} alerta(s) - {types}"
        else:
            return f"INFO: {info_count} señal(es) informativa(s)"

    def get_alerts_by_severity(
        self, alerts: List[Alert]
    ) -> Dict[AlertSeverity, List[Alert]]:
        """
        Group alerts by severity for prioritized display.

        Args:
            alerts: List of alerts to group

        Returns:
            Dictionary mapping severity levels to alert lists
        """
        grouped = {severity: [] for severity in AlertSeverity}

        for alert in alerts:
            grouped[alert.severity].append(alert)

        return grouped


__all__ = [
    "Alert",
    "AlertSeverity",
    "AlertType",
    "MarketShockDetector",
]
