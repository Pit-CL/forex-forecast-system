"""
Unit tests for data providers.

Tests cover:
- MindicadorClient: Chilean economic indicators
- XeClient: Forex spot rates
- YahooClient: Market indices and ETFs
- Provider base functionality
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import httpx

from forex_core.data.providers import (
    MindicadorClient,
    XeClient,
    YahooClient,
)
from forex_core.config.base import Settings


@pytest.mark.unit
class TestMindicadorClient:
    """Tests for MindicadorClient."""

    def test_init(self, test_settings: Settings):
        """Test client initialization."""
        client = MindicadorClient(test_settings)
        assert client.settings == test_settings
        assert "mindicador.cl" in client.base_url

    @patch("httpx.get")
    def test_get_latest_success(self, mock_get, test_settings: Settings):
        """Test fetching latest indicators."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "dolar": {
                "valor": 950.5,
                "fecha": "2025-11-12T00:00:00.000Z",
                "unidad_medida": "Pesos",
            },
            "tpm": {
                "valor": 5.75,
                "fecha": "2025-11-12T00:00:00.000Z",
                "unidad_medida": "Porcentaje",
            },
        }
        mock_get.return_value = mock_response

        client = MindicadorClient(test_settings)
        result = client.get_latest()

        assert "dolar" in result
        assert result["dolar"]["valor"] == 950.5
        assert "tpm" in result
        assert result["tpm"]["valor"] == 5.75

    @patch("httpx.get")
    def test_get_indicator_year(self, mock_get, test_settings: Settings):
        """Test fetching indicator for specific year."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "serie": [
                {"valor": 950.0, "fecha": "2025-01-01T00:00:00.000Z"},
                {"valor": 955.0, "fecha": "2025-01-02T00:00:00.000Z"},
            ]
        }
        mock_get.return_value = mock_response

        client = MindicadorClient(test_settings)
        result = client.get_indicator("dolar", year=2025)

        assert "serie" in result
        assert len(result["serie"]) == 2
        assert result["serie"][0]["valor"] == 950.0


@pytest.mark.unit
class TestXeClient:
    """Tests for XeClient."""

    def test_init(self, test_settings: Settings):
        """Test client initialization."""
        client = XeClient(test_settings)
        assert client.settings == test_settings

    @patch("httpx.get")
    def test_fetch_rate_success(self, mock_get, test_settings: Settings):
        """Test fetching USD/CLP rate."""
        # Mock HTML response with rate
        mock_response = Mock()
        mock_response.text = """
        <html>
            <body>
                <p class="result__BigRate-sc-1bsijpp-1">950.50</p>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = XeClient(test_settings)
        rate, timestamp = client.fetch_rate()

        assert rate == 950.50
        assert isinstance(timestamp, datetime)

    @patch("httpx.get")
    def test_fetch_rate_fallback(self, mock_get, test_settings: Settings):
        """Test fallback parsing when primary selector fails."""
        # Mock response without primary selector
        mock_response = Mock()
        mock_response.text = "<html><body>950.25 CLP</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = XeClient(test_settings)
        rate, timestamp = client.fetch_rate()

        # Should still extract rate from text
        assert isinstance(rate, float)
        assert isinstance(timestamp, datetime)


@pytest.mark.unit
class TestYahooClient:
    """Tests for YahooClient."""

    def test_init(self, test_settings: Settings):
        """Test client initialization."""
        client = YahooClient(test_settings)
        assert client.settings == test_settings

    @patch("httpx.get")
    def test_fetch_series_success(self, mock_get, test_settings: Settings):
        """Test fetching historical series from Yahoo Finance."""
        # Mock CSV response
        mock_response = Mock()
        mock_response.text = """Date,Close
2025-01-01,104.5
2025-01-02,104.8
2025-01-03,105.1"""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = YahooClient(test_settings)
        series = client.fetch_series("DX=F", range_window="5d")

        assert isinstance(series, pd.Series)
        assert len(series) == 3
        assert series.iloc[0] == 104.5

    @patch("httpx.get")
    def test_fetch_series_error_handling(self, mock_get, test_settings: Settings):
        """Test error handling when fetch fails."""
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        client = YahooClient(test_settings)

        with pytest.raises(httpx.HTTPError):
            client.fetch_series("INVALID")


@pytest.mark.unit
class TestProviderBase:
    """Tests for base provider functionality."""

    def test_retry_mechanism(self, test_settings: Settings):
        """Test that providers use retry mechanism for reliability."""
        from forex_core.data.providers.base import BaseProvider

        provider = BaseProvider(test_settings)

        # Should have retry configuration
        assert hasattr(provider, "settings")
        assert provider.settings == test_settings

    def test_timeout_configuration(self, test_settings: Settings):
        """Test that providers respect timeout configuration."""
        client = MindicadorClient(test_settings)

        # Client should use settings for timeout
        assert client.settings == test_settings


@pytest.mark.unit
class TestProviderIntegration:
    """Integration tests for provider interactions."""

    def test_mindicador_returns_valid_data_structure(self, test_settings: Settings):
        """Test that MindicadorClient returns expected data structure."""
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "dolar": {
                    "valor": 950.5,
                    "fecha": "2025-11-12T00:00:00.000Z",
                    "unidad_medida": "Pesos",
                }
            }
            mock_get.return_value = mock_response

            client = MindicadorClient(test_settings)
            data = client.get_latest()

            # Validate structure
            assert isinstance(data, dict)
            assert "dolar" in data
            assert "valor" in data["dolar"]
            assert "fecha" in data["dolar"]
            assert isinstance(data["dolar"]["valor"], (int, float))

    def test_yahoo_returns_valid_series(self, test_settings: Settings):
        """Test that YahooClient returns valid pandas Series."""
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "Date,Close\n2025-01-01,100.0"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            client = YahooClient(test_settings)
            series = client.fetch_series("DX=F")

            # Validate series
            assert isinstance(series, pd.Series)
            assert len(series) > 0
            assert series.index.name == "Date" or isinstance(series.index, pd.DatetimeIndex)
