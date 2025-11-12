"""
Pytest configuration and shared fixtures.

This module provides common test fixtures and configuration
for the entire test suite.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

import pytest
import pandas as pd
import numpy as np
from pydantic_settings import BaseSettings

from forex_core.data.models import Indicator
from forex_core.data.loader import DataBundle
from forex_core.data.registry import SourceRegistry
from forex_core.config.base import Settings


@pytest.fixture
def test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """
    Create test settings with temporary directories.

    Args:
        tmp_path: Pytest temporary directory
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Test configuration settings
    """
    # Disable .env file loading for tests
    monkeypatch.setenv("ENVIRONMENT", "testing")

    # Create test environment
    test_env = {
        "ENVIRONMENT": "testing",
        "DATA_DIR": str(tmp_path / "data"),
        "OUTPUT_DIR": str(tmp_path / "output"),
        "CACHE_DIR": str(tmp_path / "cache"),
        "GMAIL_USER": "test@example.com",
        "GMAIL_APP_PASSWORD": "test_password",
        "EMAIL_RECIPIENTS": "recipient@example.com",
        "FRED_API_KEY": "test_fred_key",
        "NEWS_API_KEY": "test_news_key",
    }

    # Create settings with test environment, bypassing .env
    settings = Settings(_env_file=None, **test_env)

    # Create directories (note: lowercase attribute names)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

    # Cache dir might not exist in Settings, skip if not present
    if hasattr(settings, 'cache_dir'):
        Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)

    return settings


@pytest.fixture
def sample_usdclp_series() -> pd.Series:
    """
    Create sample USD/CLP time series.

    Returns:
        Pandas Series with 180 days of synthetic USD/CLP data
    """
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    # Generate realistic-looking USD/CLP data around 950
    base = 950.0
    values = base + pd.Series(range(180)).apply(
        lambda x: 20 * np.sin(x / 10) + np.random.randn() * 5
    )
    return pd.Series(values.values, index=dates, name="usdclp")


@pytest.fixture
def sample_copper_series() -> pd.Series:
    """Create sample copper price time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    base = 3.85
    values = base + pd.Series(range(180)).apply(
        lambda x: 0.15 * np.sin(x / 15) + np.random.randn() * 0.05
    )
    return pd.Series(values.values, index=dates, name="copper")


@pytest.fixture
def sample_tpm_series() -> pd.Series:
    """Create sample TPM (Chilean policy rate) time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    # TPM stays constant for periods then steps
    values = pd.Series([5.75] * 180, index=dates, name="tpm")
    return values


@pytest.fixture
def sample_inflation_series() -> pd.Series:
    """Create sample inflation (IPC) time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    base = 0.3
    values = base + pd.Series(range(180)).apply(
        lambda x: 0.1 * np.sin(x / 20) + np.random.randn() * 0.05
    )
    return pd.Series(values.values, index=dates, name="ipc")


@pytest.fixture
def sample_dxy_series() -> pd.Series:
    """Create sample DXY (Dollar Index) time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    base = 104.5
    values = base + pd.Series(range(180)).apply(
        lambda x: 2.0 * np.sin(x / 12) + np.random.randn() * 0.3
    )
    return pd.Series(values.values, index=dates, name="dxy")


@pytest.fixture
def sample_vix_series() -> pd.Series:
    """Create sample VIX (volatility index) time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    base = 15.0
    values = base + pd.Series(range(180)).apply(
        lambda x: 3.0 * np.sin(x / 8) + np.random.randn() * 1.0
    )
    # VIX is always positive
    values = values.apply(lambda x: max(x, 10.0))
    return pd.Series(values.values, index=dates, name="vix")


@pytest.fixture
def sample_eem_series() -> pd.Series:
    """Create sample EEM (Emerging Markets ETF) time series."""
    dates = pd.date_range(end=datetime.now(), periods=180, freq="D")
    base = 40.0
    values = base + pd.Series(range(180)).apply(
        lambda x: 2.5 * np.sin(x / 10) + np.random.randn() * 0.5
    )
    return pd.Series(values.values, index=dates, name="eem")


@pytest.fixture
def sample_indicators() -> Dict[str, Indicator]:
    """
    Create sample economic indicators.

    Returns:
        Dictionary of sample indicators
    """
    now = datetime.now()

    return {
        "usdclp_spot": Indicator(
            name="USD/CLP Spot",
            value=950.5,
            unit="CLP",
            timestamp=now,
            source_id=1,
        ),
        "copper": Indicator(
            name="Copper Price",
            value=3.85,
            unit="USD/lb",
            timestamp=now,
            source_id=2,
        ),
        "tpm": Indicator(
            name="TPM",
            value=5.75,
            unit="%",
            timestamp=now,
            source_id=3,
        ),
        "fed_target": Indicator(
            name="Fed Funds Target",
            value=5.50,
            unit="%",
            timestamp=now,
            source_id=4,
        ),
        "dxy": Indicator(
            name="DXY Index",
            value=104.5,
            unit="index",
            timestamp=now,
            source_id=5,
        ),
        "ipc": Indicator(
            name="IPC Chile",
            value=0.3,
            unit="%",
            timestamp=now,
            source_id=6,
        ),
    }


@pytest.fixture
def sample_data_bundle(
    sample_usdclp_series: pd.Series,
    sample_copper_series: pd.Series,
    sample_tpm_series: pd.Series,
    sample_inflation_series: pd.Series,
    sample_dxy_series: pd.Series,
    sample_vix_series: pd.Series,
    sample_eem_series: pd.Series,
    sample_indicators: Dict[str, Indicator],
) -> DataBundle:
    """
    Create sample data bundle for testing.

    Args:
        sample_usdclp_series: Sample USD/CLP series
        sample_copper_series: Sample copper series
        sample_tpm_series: Sample TPM series
        sample_inflation_series: Sample inflation series
        sample_dxy_series: Sample DXY series
        sample_vix_series: Sample VIX series
        sample_eem_series: Sample EEM series
        sample_indicators: Sample indicators

    Returns:
        Complete DataBundle for testing
    """
    sources = SourceRegistry()
    sources.add(
        category="Banco Central",
        name="Banco Central de Chile",
        url="https://si3.bcentral.cl/indicadoressiete",
        timestamp=datetime.now(),
        note="Test source",
    )

    # Next FOMC meeting (30 days from now)
    next_fomc = datetime.now() + pd.Timedelta(days=30)

    return DataBundle(
        usdclp_series=sample_usdclp_series,
        copper_series=sample_copper_series,
        tpm_series=sample_tpm_series,
        inflation_series=sample_inflation_series,
        dxy_series=sample_dxy_series,
        vix_series=sample_vix_series,
        eem_series=sample_eem_series,
        indicators=sample_indicators,
        sources=sources,
        macro_events=[],
        news=[],
        fed_dot_plot={"2025": 4.5},
        fed_dot_source_id=1,
        next_fomc=next_fomc,
        rate_differential=0.25,
        usdclp_intraday=None,
    )
