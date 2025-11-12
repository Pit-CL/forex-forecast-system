"""
Simple unit tests for analysis modules.

Tests cover basic functionality of technical and fundamental analysis.
"""

import pandas as pd
import pytest
import numpy as np

from forex_core.analysis import technical
from forex_core.data.loader import DataBundle


@pytest.mark.unit
class TestTechnicalAnalysis:
    """Tests for technical analysis functions."""

    def test_compute_technicals_returns_dict(self, sample_usdclp_series: pd.Series):
        """Test that compute_technicals returns a dictionary."""
        result = technical.compute_technicals(sample_usdclp_series)

        assert isinstance(result, dict)
        # Should have some indicators
        assert len(result) > 0

    def test_rsi_calculation_returns_series(self, sample_usdclp_series: pd.Series):
        """Test that RSI calculation returns a Series."""
        rsi_series = technical.calculate_rsi(sample_usdclp_series, period=14)

        assert isinstance(rsi_series, pd.Series)
        assert len(rsi_series) == len(sample_usdclp_series)

    def test_macd_calculation_returns_two_series(self, sample_usdclp_series: pd.Series):
        """Test that MACD returns two series."""
        macd, signal = technical.calculate_macd(sample_usdclp_series)

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
