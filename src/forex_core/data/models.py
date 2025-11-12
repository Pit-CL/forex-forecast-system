"""
Data models for forex forecasting system.

This module defines Pydantic models for structured data used throughout
the forecasting pipeline. All models support validation, serialization,
and type safety.

Models:
    - Indicator: Economic/market indicator with metadata
    - MacroEvent: Scheduled macroeconomic event
    - NewsHeadline: News article with sentiment
    - ForecastPoint: Single forecast datapoint with confidence intervals
    - ForecastPackage: Complete forecast with methodology and metrics
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Indicator(BaseModel):
    """
    Economic or market indicator with metadata and source tracking.

    Attributes:
        name: Human-readable indicator name.
        value: Numeric value of the indicator.
        unit: Unit of measurement (e.g., "CLP", "%", "pts").
        timestamp: When this value was recorded or published.
        source_id: Reference to source in SourceRegistry.
        metadata: Optional additional key-value metadata.

    Example:
        >>> indicator = Indicator(
        ...     name="USD/CLP spot",
        ...     value=950.25,
        ...     unit="CLP",
        ...     timestamp=dt.datetime.now(),
        ...     source_id=1
        ... )
    """

    name: str = Field(description="Indicator name")
    value: float = Field(description="Numeric value")
    unit: str = Field(description="Unit of measurement")
    timestamp: dt.datetime = Field(description="Observation timestamp")
    source_id: int = Field(description="Source registry reference")
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional metadata"
    )


class MacroEvent(BaseModel):
    """
    Scheduled macroeconomic event (e.g., FOMC meeting, GDP release).

    Attributes:
        title: Event name/description.
        country: ISO-3 country code (USD for US events).
        datetime: Scheduled event datetime.
        impact: Expected market impact ("High", "Medium", "Low").
        actual: Actual released value (if available).
        forecast: Market consensus forecast.
        previous: Previous period value.
        source_id: Reference to source in SourceRegistry.

    Example:
        >>> event = MacroEvent(
        ...     title="FOMC Rate Decision",
        ...     country="USD",
        ...     datetime=datetime(2025, 12, 15, 14, 0),
        ...     impact="High",
        ...     forecast="5.25%",
        ...     source_id=3
        ... )
    """

    title: str = Field(description="Event title")
    country: str = Field(description="Country code (ISO-3)")
    datetime: dt.datetime = Field(description="Event datetime")
    impact: str = Field(description="Impact level (High/Medium/Low)")
    actual: Optional[str] = Field(default=None, description="Actual value released")
    forecast: Optional[str] = Field(default=None, description="Market forecast")
    previous: Optional[str] = Field(default=None, description="Previous value")
    source_id: int = Field(description="Source registry reference")


class NewsHeadline(BaseModel):
    """
    News article headline with sentiment analysis.

    Attributes:
        title: Article headline text.
        url: Full URL to article.
        published_at: Publication timestamp.
        source: News source name (e.g., "Reuters", "Bloomberg").
        sentiment: Sentiment classification ("Positive", "Negative", "Neutral").
        source_id: Reference to source in SourceRegistry.

    Example:
        >>> news = NewsHeadline(
        ...     title="Chilean Central Bank holds rates steady",
        ...     url="https://example.com/article",
        ...     published_at=dt.datetime.now(),
        ...     source="Reuters",
        ...     sentiment="Neutral",
        ...     source_id=5
        ... )
    """

    title: str = Field(description="Article headline")
    url: str = Field(description="Article URL")
    published_at: dt.datetime = Field(description="Publication datetime")
    source: str = Field(description="News source name")
    sentiment: str = Field(description="Sentiment (Positive/Negative/Neutral)")
    source_id: int = Field(description="Source registry reference")


class ForecastPoint(BaseModel):
    """
    Single forecast point with confidence intervals.

    Attributes:
        date: Forecast date.
        mean: Point forecast (mean prediction).
        ci80_low: Lower bound of 80% confidence interval.
        ci80_high: Upper bound of 80% confidence interval.
        ci95_low: Lower bound of 95% confidence interval.
        ci95_high: Upper bound of 95% confidence interval.
        std_dev: Standard deviation of forecast distribution.

    Example:
        >>> point = ForecastPoint(
        ...     date=datetime(2025, 12, 31),
        ...     mean=945.0,
        ...     ci80_low=935.0,
        ...     ci80_high=955.0,
        ...     ci95_low=925.0,
        ...     ci95_high=965.0,
        ...     std_dev=8.5
        ... )
    """

    date: dt.datetime = Field(description="Forecast date")
    mean: float = Field(description="Point forecast (mean)")
    ci80_low: float = Field(description="80% CI lower bound")
    ci80_high: float = Field(description="80% CI upper bound")
    ci95_low: float = Field(description="95% CI lower bound")
    ci95_high: float = Field(description="95% CI upper bound")
    std_dev: float = Field(description="Standard deviation")


class ForecastPackage(BaseModel):
    """
    Complete forecast package with methodology and quality metrics.

    Attributes:
        series: List of forecast points.
        methodology: Forecasting method description.
        error_metrics: Dictionary of error metrics (RMSE, MAE, MAPE).
        residual_vol: Residual volatility estimate.

    Example:
        >>> package = ForecastPackage(
        ...     series=[point1, point2, point3],
        ...     methodology="ARIMA(2,1,2) with seasonal adjustment",
        ...     error_metrics={"rmse": 5.2, "mae": 3.8, "mape": 0.4},
        ...     residual_vol=4.1
        ... )
    """

    series: List[ForecastPoint] = Field(description="Forecast points")
    methodology: str = Field(description="Forecasting methodology")
    error_metrics: Dict[str, float] = Field(description="Error metrics")
    residual_vol: float = Field(description="Residual volatility")


# Alias for compatibility
ForecastResult = ForecastPackage

__all__ = [
    "Indicator",
    "MacroEvent",
    "NewsHeadline",
    "ForecastPoint",
    "ForecastPackage",
    "ForecastResult",  # Alias
]
