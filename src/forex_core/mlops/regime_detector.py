"""
Market Regime Detector for USD/CLP Forecasting.

Detecta regímenes de mercado para ajustar dinámicamente los modelos de forecasting
y los intervalos de confianza. Específico para USD/CLP con consideraciones del
mercado chileno.

Regímenes Detectados:
- NORMAL: Volatilidad normal, sin eventos extraordinarios
- HIGH_VOL: Alta volatilidad (>2σ histórica)
- COPPER_SHOCK: Movimientos bruscos en precio del cobre (principal export chileno)
- BCCH_INTERVENTION: Posible intervención del Banco Central de Chile

References:
- Hamilton, J.D. (1989). "A New Approach to the Economic Analysis of
  Nonstationary Time Series and the Business Cycle"
- Pagan, A.R., & Sossounov, K.A. (2003). "A Simple Framework for Analysing
  Bull and Bear Markets"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats


class MarketRegime(str, Enum):
    """Regímenes de mercado para USD/CLP."""

    NORMAL = "normal"  # Volatilidad normal
    HIGH_VOL = "high_vol"  # Alta volatilidad
    COPPER_SHOCK = "copper_shock"  # Shock en precio del cobre
    BCCH_INTERVENTION = "bcch_intervention"  # Posible intervención BCCh
    UNKNOWN = "unknown"  # No hay suficiente data


@dataclass
class RegimeSignals:
    """
    Señales individuales para detección de régimen.

    Attributes:
        vol_z_score: Z-score de volatilidad actual vs histórica.
        vol_percentile: Percentil de volatilidad (0-100).
        copper_change: Cambio % del cobre en últimos 5 días.
        usdclp_change: Cambio % USD/CLP en últimos 5 días.
        correlation_break: Ruptura de correlación USD/CLP-Copper (bool).
        bcch_meeting_近proximity: Días hasta/desde reunión BCCh más cercana.
    """

    vol_z_score: float
    vol_percentile: float
    copper_change: float
    usdclp_change: float
    correlation_break: bool
    bcch_meeting_proximity: int


@dataclass
class RegimeReport:
    """
    Reporte de detección de régimen de mercado.

    Attributes:
        regime: Régimen detectado.
        confidence: Nivel de confianza (0-100).
        signals: Señales que contribuyeron a la decisión.
        timestamp: Cuándo se realizó la detección.
        recommendation: Recomendación de acción.
        volatility_multiplier: Factor para ajustar CIs (1.0 = normal, >1.0 = expandir).
    """

    regime: MarketRegime
    confidence: float
    signals: RegimeSignals
    timestamp: datetime
    recommendation: str
    volatility_multiplier: float

    def requires_wider_ci(self) -> bool:
        """Check if regime requires wider confidence intervals."""
        return self.regime in [
            MarketRegime.HIGH_VOL,
            MarketRegime.COPPER_SHOCK,
            MarketRegime.BCCH_INTERVENTION,
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "regime": self.regime.value,
            "confidence": self.confidence,
            "vol_z_score": self.signals.vol_z_score,
            "vol_percentile": self.signals.vol_percentile,
            "copper_change": self.signals.copper_change,
            "usdclp_change": self.signals.usdclp_change,
            "correlation_break": self.signals.correlation_break,
            "bcch_meeting_proximity": self.signals.bcch_meeting_proximity,
            "timestamp": self.timestamp,
            "recommendation": self.recommendation,
            "volatility_multiplier": self.volatility_multiplier,
        }


class MarketRegimeDetector:
    """
    Detector de regímenes de mercado para USD/CLP.

    Analiza volatilidad, correlación con cobre, y calendario BCCh para
    identificar el régimen actual del mercado.

    Attributes:
        lookback_days: Días de historia para calcular baseline (default: 90).
        vol_threshold_high: Z-score para considerar alta volatilidad (default: 2.0).
        copper_threshold: Cambio % del cobre para shock (default: 5.0).
        bcch_meeting_days: Días alrededor de reunión BCCh sensibles (default: 3).

    Example:
        >>> detector = MarketRegimeDetector()
        >>> report = detector.detect(usdclp_series, copper_series)
        >>> if report.regime == MarketRegime.HIGH_VOL:
        ...     print(f"Alta volatilidad - usar CI multiplier: {report.volatility_multiplier}")
    """

    def __init__(
        self,
        lookback_days: int = 90,
        vol_threshold_high: float = 2.0,
        copper_threshold: float = 5.0,
        bcch_meeting_days: int = 3,
    ):
        """
        Initialize regime detector.

        Args:
            lookback_days: Days of history for baseline calculation.
            vol_threshold_high: Z-score threshold for high volatility.
            copper_threshold: Copper % change threshold for shock detection.
            bcch_meeting_days: Days around BCCh meeting considered sensitive.
        """
        self.lookback_days = lookback_days
        self.vol_threshold_high = vol_threshold_high
        self.copper_threshold = copper_threshold
        self.bcch_meeting_days = bcch_meeting_days

        logger.info(
            f"MarketRegimeDetector initialized: lookback={lookback_days}d, "
            f"vol_threshold={vol_threshold_high}σ"
        )

    def detect(
        self,
        usdclp_series: pd.Series,
        copper_series: Optional[pd.Series] = None,
    ) -> RegimeReport:
        """
        Detect current market regime.

        Args:
            usdclp_series: USD/CLP price series (daily).
            copper_series: Copper price series (optional, for better detection).

        Returns:
            RegimeReport with detected regime and recommendations.

        Example:
            >>> report = detector.detect(usdclp_series, copper_series)
            >>> print(f"Regime: {report.regime.value}")
            >>> print(f"Confidence: {report.confidence:.1f}%")
        """
        logger.info("Starting market regime detection")

        try:
            # Calculate signals
            signals = self._calculate_signals(usdclp_series, copper_series)

            # Detect regime based on signals
            regime, confidence = self._classify_regime(signals)

            # Generate recommendation
            recommendation = self._generate_recommendation(regime, signals)

            # Calculate volatility multiplier
            vol_multiplier = self._calculate_volatility_multiplier(regime, signals)

            report = RegimeReport(
                regime=regime,
                confidence=confidence,
                signals=signals,
                timestamp=datetime.now(),
                recommendation=recommendation,
                volatility_multiplier=vol_multiplier,
            )

            logger.info(
                f"Regime detected: {regime.value} (confidence: {confidence:.1f}%, "
                f"vol_multiplier: {vol_multiplier:.2f}x)"
            )

            return report

        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            # Return UNKNOWN regime as fallback
            return self._create_unknown_report()

    def _calculate_signals(
        self,
        usdclp_series: pd.Series,
        copper_series: Optional[pd.Series],
    ) -> RegimeSignals:
        """Calculate individual regime signals."""
        # Ensure sufficient data
        if len(usdclp_series) < self.lookback_days:
            logger.warning(
                f"Insufficient data: {len(usdclp_series)} days < {self.lookback_days} required"
            )
            return self._create_empty_signals()

        # Calculate log returns
        log_returns = np.log(usdclp_series).diff().dropna()

        # 1. Volatility analysis
        recent_vol = log_returns.tail(30).std()  # Last 30 days
        historical_vol = log_returns.tail(self.lookback_days).std()
        vol_mean = log_returns.tail(self.lookback_days).std()
        vol_std = log_returns.tail(self.lookback_days).rolling(30).std().std()

        vol_z_score = (recent_vol - vol_mean) / (vol_std + 1e-10)
        vol_percentile = (
            stats.percentileofscore(
                log_returns.tail(self.lookback_days).rolling(30).std().dropna(),
                recent_vol,
            )
        )

        # 2. Copper analysis (if available)
        copper_change = 0.0
        correlation_break = False

        if copper_series is not None and len(copper_series) >= 30:
            # Align copper series with USD/CLP
            copper_aligned = copper_series.reindex(usdclp_series.index).ffill()

            # Recent copper change (last 5 days)
            if len(copper_aligned) >= 5:
                copper_change = (
                    (copper_aligned.iloc[-1] - copper_aligned.iloc[-6])
                    / copper_aligned.iloc[-6]
                    * 100
                )

            # Check correlation break
            # Historical correlation (90 days)
            if len(copper_aligned) >= self.lookback_days:
                copper_returns = np.log(copper_aligned).diff().dropna()
                common_idx = log_returns.index.intersection(copper_returns.index)

                if len(common_idx) >= 60:
                    historical_corr = log_returns.loc[common_idx].tail(90).corr(
                        copper_returns.loc[common_idx].tail(90)
                    )

                    # Recent correlation (30 days)
                    recent_corr = log_returns.loc[common_idx].tail(30).corr(
                        copper_returns.loc[common_idx].tail(30)
                    )

                    # Correlation break: recent << historical
                    # Normal USD/CLP-Copper correlation: ~0.6-0.7
                    if abs(historical_corr - recent_corr) > 0.3:
                        correlation_break = True
                        logger.info(
                            f"Correlation break detected: hist={historical_corr:.2f}, "
                            f"recent={recent_corr:.2f}"
                        )

        # 3. USD/CLP recent change
        usdclp_change = (
            (usdclp_series.iloc[-1] - usdclp_series.iloc[-6])
            / usdclp_series.iloc[-6]
            * 100
        )

        # 4. BCCh meeting proximity
        bcch_meeting_proximity = self._get_bcch_meeting_proximity()

        return RegimeSignals(
            vol_z_score=float(vol_z_score),
            vol_percentile=float(vol_percentile),
            copper_change=float(copper_change),
            usdclp_change=float(usdclp_change),
            correlation_break=correlation_break,
            bcch_meeting_proximity=bcch_meeting_proximity,
        )

    def _classify_regime(
        self, signals: RegimeSignals
    ) -> tuple[MarketRegime, float]:
        """
        Classify market regime based on signals.

        Returns:
            Tuple of (regime, confidence_percentage).
        """
        # Decision tree for regime classification
        confidence = 0.0

        # Check for BCCh intervention first (highest priority)
        if abs(signals.bcch_meeting_proximity) <= self.bcch_meeting_days:
            # Near BCCh meeting + high volatility
            if signals.vol_z_score > 1.5:
                confidence = min(
                    80 + signals.vol_z_score * 5, 95
                )  # Max 95% confidence
                return MarketRegime.BCCH_INTERVENTION, confidence

        # Check for copper shock
        if abs(signals.copper_change) > self.copper_threshold:
            # Large copper movement + correlation break
            if signals.correlation_break:
                confidence = min(70 + abs(signals.copper_change), 90)
                return MarketRegime.COPPER_SHOCK, confidence

        # Check for high volatility
        if signals.vol_z_score > self.vol_threshold_high:
            # High vol percentile confirms
            if signals.vol_percentile > 80:
                confidence = min(60 + signals.vol_percentile / 5, 85)
                return MarketRegime.HIGH_VOL, confidence

        # Default: NORMAL regime
        # Confidence based on how "normal" the signals are
        normality_score = 100 - min(
            abs(signals.vol_z_score) * 20
            + abs(signals.copper_change)
            + (signals.vol_percentile - 50),
            50,
        )
        confidence = max(normality_score, 50)

        return MarketRegime.NORMAL, confidence

    def _generate_recommendation(
        self, regime: MarketRegime, signals: RegimeSignals
    ) -> str:
        """Generate actionable recommendation based on regime."""
        if regime == MarketRegime.NORMAL:
            return (
                "Régimen normal. Mantener configuración estándar de modelos. "
                "Intervalos de confianza estándar."
            )

        elif regime == MarketRegime.HIGH_VOL:
            return (
                f"ALTA VOLATILIDAD detectada (z-score: {signals.vol_z_score:.2f}σ). "
                f"Recomendaciones: (1) Expandir intervalos de confianza 1.5x-2x, "
                f"(2) Aumentar frecuencia de re-entrenamiento, "
                f"(3) Considerar modelos robustos a outliers."
            )

        elif regime == MarketRegime.COPPER_SHOCK:
            return (
                f"SHOCK EN PRECIO DEL COBRE ({signals.copper_change:+.1f}% en 5 días). "
                f"Recomendaciones: (1) Verificar modelos VAR (incorporan cobre), "
                f"(2) Expandir CIs 1.5x, "
                f"(3) Monitorear correlación USD/CLP-Copper."
            )

        elif regime == MarketRegime.BCCH_INTERVENTION:
            return (
                f"Proximidad a reunión BCCh ({signals.bcch_meeting_proximity:+d} días). "
                f"Recomendaciones: (1) Expandir CIs 2x alrededor de decisión TPM, "
                f"(2) Revisar forecasts post-reunión, "
                f"(3) Monitorear comunicados BCCh."
            )

        else:
            return "Régimen desconocido. Usar configuración conservadora."

    def _calculate_volatility_multiplier(
        self, regime: MarketRegime, signals: RegimeSignals
    ) -> float:
        """
        Calculate CI volatility multiplier based on regime.

        Returns:
            Multiplier for confidence intervals (1.0 = normal, >1.0 = wider).
        """
        if regime == MarketRegime.NORMAL:
            return 1.0

        elif regime == MarketRegime.HIGH_VOL:
            # Scale with z-score: 1.5x at 2σ, up to 2.5x at 4σ
            return min(1.0 + signals.vol_z_score * 0.25, 2.5)

        elif regime == MarketRegime.COPPER_SHOCK:
            # Fixed 1.5x for copper shocks
            return 1.5

        elif regime == MarketRegime.BCCH_INTERVENTION:
            # 2x around BCCh meetings
            return 2.0

        else:
            # Conservative: 1.5x for unknown
            return 1.5

    def _get_bcch_meeting_proximity(self) -> int:
        """
        Calculate days to/from nearest BCCh monetary policy meeting.

        BCCh meets on 3rd Tuesday of each month (typically).

        Returns:
            Days to next meeting (positive) or since last meeting (negative).
        """
        today = datetime.now()

        # Find 3rd Tuesday of current month
        current_month_third_tuesday = self._get_third_tuesday(
            today.year, today.month
        )

        # If we've passed it, check next month
        if today.date() > current_month_third_tuesday:
            # Next month
            next_month = today.month + 1
            next_year = today.year
            if next_month > 12:
                next_month = 1
                next_year += 1

            next_meeting = self._get_third_tuesday(next_year, next_month)
            days_to_next = (
                datetime.combine(next_meeting, datetime.min.time()) - today
            ).days

            return days_to_next

        else:
            # This month's meeting is upcoming
            days_to_next = (
                datetime.combine(current_month_third_tuesday, datetime.min.time())
                - today
            ).days
            return days_to_next

    def _get_third_tuesday(self, year: int, month: int) -> datetime.date:
        """Get the 3rd Tuesday of a given month."""
        # First day of month
        first_day = datetime(year, month, 1)

        # Find first Tuesday
        days_until_tuesday = (1 - first_day.weekday()) % 7  # Tuesday = 1
        first_tuesday = first_day + timedelta(days=days_until_tuesday)

        # Third Tuesday = first Tuesday + 14 days
        third_tuesday = first_tuesday + timedelta(days=14)

        return third_tuesday.date()

    def _create_empty_signals(self) -> RegimeSignals:
        """Create empty signals for insufficient data case."""
        return RegimeSignals(
            vol_z_score=0.0,
            vol_percentile=50.0,
            copper_change=0.0,
            usdclp_change=0.0,
            correlation_break=False,
            bcch_meeting_proximity=999,
        )

    def _create_unknown_report(self) -> RegimeReport:
        """Create UNKNOWN regime report for error cases."""
        return RegimeReport(
            regime=MarketRegime.UNKNOWN,
            confidence=0.0,
            signals=self._create_empty_signals(),
            timestamp=datetime.now(),
            recommendation="Datos insuficientes para detección de régimen. Usar configuración conservadora.",
            volatility_multiplier=1.5,  # Conservative default
        )


__all__ = [
    "MarketRegime",
    "RegimeSignals",
    "RegimeReport",
    "MarketRegimeDetector",
]
