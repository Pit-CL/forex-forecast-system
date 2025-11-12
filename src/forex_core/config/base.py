"""
Base configuration using Pydantic Settings.

This module provides the main Settings class that loads configuration from
environment variables or .env files. It supports:
- Directory paths (data, output, charts, warehouse)
- API keys (FRED, NewsAPI, AlphaVantage)
- External service URLs
- Email configuration (Gmail)
- Model configuration (ARIMA, VAR, RF toggles)
- Proxy settings
- Cache settings

The Settings class uses Pydantic for validation and type safety.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import EmailStr, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from zoneinfo import ZoneInfo

from .constants import DEFAULT_RECIPIENTS


class Settings(BaseSettings):
    """
    Global configuration loaded from environment variables or .env file.

    All settings can be overridden by environment variables using the specified aliases.
    Directories are created automatically if they don't exist.

    Example:
        >>> settings = get_settings()
        >>> print(settings.data_dir)
        PosixPath('./data')
        >>> print(settings.environment)
        'production'
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General settings
    environment: str = Field(
        default="production",
        alias="ENVIRONMENT",
        description="Deployment environment (production, staging, development)",
    )
    report_timezone: str = Field(
        default="America/Santiago",
        alias="REPORT_TIMEZONE",
        description="Timezone for report generation and scheduling",
    )

    # Directory paths
    data_dir: Path = Field(
        default=Path("./data"),
        alias="DATA_DIR",
        description="Directory for data storage",
    )
    output_dir: Path = Field(
        default=Path("./reports"),
        alias="OUTPUT_DIR",
        description="Directory for generated reports",
    )
    chart_dir: Path = Field(
        default=Path("./charts"),
        alias="CHART_DIR",
        description="Directory for chart images",
    )
    warehouse_dir: Path = Field(
        default=Path("./data/warehouse"),
        alias="WAREHOUSE_DIR",
        description="Directory for data warehouse/historical data",
    )
    metrics_log_path: Path = Field(
        default=Path("./logs/metrics.jsonl"),
        alias="METRICS_LOG_PATH",
        description="Path to metrics log file (JSONL format)",
    )

    # Cache settings
    cache_ttl_minutes: int = Field(
        default=30,
        alias="CACHE_TTL_MINUTES",
        description="Cache time-to-live in minutes",
    )

    # API Keys
    fred_api_key: Optional[str] = Field(
        default=None,
        alias="FRED_API_KEY",
        description="Federal Reserve Economic Data API key",
    )
    news_api_key: Optional[str] = Field(
        default=None,
        alias="NEWS_API_KEY",
        description="NewsAPI.org API key for news data",
    )
    news_query: str = Field(
        default="Banco Central de Chile",
        alias="NEWS_QUERY",
        description="Search query for news articles",
    )
    alphavantage_api_key: Optional[str] = Field(
        default=None,
        alias="ALPHAVANTAGE_API_KEY",
        description="Alpha Vantage API key for financial data",
    )

    # External service URLs
    mindicador_base_url: HttpUrl = Field(
        default="https://mindicador.cl/api",
        alias="MINDICADOR_BASE_URL",
        description="Base URL for MindicadorCL API (Chilean economic indicators)",
    )
    stooq_base_url: HttpUrl = Field(
        default="https://stooq.com/q/d/l/",
        alias="STOOQ_BASE_URL",
        description="Base URL for Stooq historical data downloads",
    )
    xe_converter_url: HttpUrl = Field(
        default="https://www.xe.com/currencyconverter/convert/",
        alias="XE_CONVERTER_URL",
        description="XE.com currency converter URL",
    )
    macro_events_url: HttpUrl = Field(
        default="https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        alias="MACRO_EVENTS_URL",
        description="URL for macroeconomic events calendar",
    )

    # Email configuration
    gmail_user: Optional[EmailStr] = Field(
        default=None,
        alias="GMAIL_USER",
        description="Gmail username for sending reports",
    )
    gmail_app_password: Optional[str] = Field(
        default=None,
        alias="GMAIL_APP_PASSWORD",
        description="Gmail app password (not regular password)",
    )
    email_recipients: List[EmailStr] = Field(
        default_factory=lambda: list(DEFAULT_RECIPIENTS),
        alias="EMAIL_RECIPIENTS",
        description="Comma-separated list of email recipients",
    )

    # Proxy settings
    http_proxy: Optional[str] = Field(
        default=None,
        alias="HTTP_PROXY",
        description="HTTP proxy URL if required",
    )

    # Model configuration
    enable_arima: bool = Field(
        default=True,
        alias="ENABLE_ARIMA",
        description="Enable ARIMA forecasting model",
    )
    enable_var: bool = Field(
        default=True,
        alias="ENABLE_VAR",
        description="Enable VAR (Vector Autoregression) forecasting model",
    )
    enable_rf: bool = Field(
        default=True,
        alias="ENABLE_RF",
        description="Enable Random Forest forecasting model",
    )
    ensemble_window: int = Field(
        default=30,
        alias="ENSEMBLE_WINDOW",
        description="Window size for ensemble model weighting",
    )

    @field_validator("email_recipients", mode="before")
    @classmethod
    def _parse_recipients(cls, value: Any) -> List[str]:
        """
        Parse email recipients from string or list.

        Supports comma-separated strings or lists of email addresses.

        Args:
            value: String or list of email addresses.

        Returns:
            List of email addresses.
        """
        if isinstance(value, str):
            return [token.strip() for token in value.split(",") if token.strip()]
        return value

    def ensure_directories(self) -> None:
        """
        Create all configured directories if they don't exist.

        This is called automatically by get_settings() to ensure
        the application has all necessary directories.

        Example:
            >>> settings = Settings()
            >>> settings.ensure_directories()
            # All directories now exist
        """
        for directory in (
            self.data_dir,
            self.output_dir,
            self.chart_dir,
            self.warehouse_dir,
            self.metrics_log_path.parent,
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)

    @property
    def proxy(self) -> Optional[str]:
        """
        Get proxy URL as string or None.

        Returns:
            Proxy URL string or None if not configured.
        """
        return str(self.http_proxy) if self.http_proxy else None

    @property
    def tz(self) -> ZoneInfo:
        """
        Get timezone object from configured timezone string.

        Returns:
            ZoneInfo object for the configured timezone.

        Example:
            >>> settings = get_settings()
            >>> tz = settings.tz
            >>> print(tz)
            zoneinfo.ZoneInfo(key='America/Santiago')
        """
        return ZoneInfo(self.report_timezone)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get or create the singleton Settings instance.

    This function is cached to ensure only one Settings instance exists.
    Automatically creates all required directories.

    Returns:
        Configured Settings instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.environment)
        'production'
        >>> # Second call returns cached instance
        >>> settings2 = get_settings()
        >>> assert settings is settings2
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


__all__ = ["Settings", "get_settings"]
