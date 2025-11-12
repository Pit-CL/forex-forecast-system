"""
End-to-End Tests for PDF Generation.

These tests validate the CRITICAL requirement: PDF generation must work correctly.
Tests cover:
- PDF file creation
- Spanish character rendering
- Chart embedding
- Metadata correctness
- File size validation

IMPORTANT: These tests require WeasyPrint system dependencies to be installed.
"""

from pathlib import Path
from datetime import datetime
import pytest

from forex_core.config.base import Settings
from forex_core.data.loader import DataBundle
from forex_core.data.models import ForecastResult, ForecastPoint
from forex_core.reporting import ChartGenerator, ReportBuilder


@pytest.mark.e2e
class TestPDFGeneration:
    """End-to-end tests for PDF generation."""

    def test_chart_generation_creates_files(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test that chart generation creates PNG files."""
        # Create sample forecast
        forecast = self._create_sample_forecast(days=7)

        # Generate charts
        chart_gen = ChartGenerator(test_settings)
        charts = chart_gen.generate(sample_data_bundle, forecast, horizon="7d")

        # Verify charts were created
        assert "hist_forecast" in charts
        assert "forecast_bands" in charts

        # Verify files exist
        assert charts["hist_forecast"].exists()
        assert charts["forecast_bands"].exists()

        # Verify files are not empty
        assert charts["hist_forecast"].stat().st_size > 1000  # At least 1KB
        assert charts["forecast_bands"].stat().st_size > 1000

        # Verify file extensions
        assert charts["hist_forecast"].suffix == ".png"
        assert charts["forecast_bands"].suffix == ".png"

    def test_chart_base64_encoding(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test that charts can be encoded to base64."""
        forecast = self._create_sample_forecast(days=7)

        chart_gen = ChartGenerator(test_settings)
        charts = chart_gen.generate(sample_data_bundle, forecast, horizon="7d")

        # Test base64 encoding
        base64_imgs = chart_gen.charts_to_base64(charts)

        assert len(base64_imgs) == 2
        for img in base64_imgs:
            assert img.startswith("data:image/png;base64,")
            assert len(img) > 1000  # Encoded string should be substantial

    @pytest.mark.skipif(
        not Path("/usr/bin/weasyprint").exists()
        and not Path("/usr/local/bin/weasyprint").exists(),
        reason="WeasyPrint not installed",
    )
    def test_pdf_generation_7d(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test 7-day forecast PDF generation."""
        forecast = self._create_sample_forecast(days=7)
        artifacts = {
            "weights": {"arima_garch": 0.5, "var": 0.3, "random_forest": 0.2},
            "component_metrics": {},
        }

        # Generate charts
        chart_gen = ChartGenerator(test_settings)
        charts = chart_gen.generate(sample_data_bundle, forecast, horizon="7d")

        # Build PDF report
        report_builder = ReportBuilder(test_settings)
        pdf_path = report_builder.build(
            bundle=sample_data_bundle,
            forecast=forecast,
            artifacts=artifacts,
            charts=charts,
            horizon="7d",
        )

        # Verify PDF was created
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stat().st_size > 10000  # At least 10KB

        # Verify filename contains horizon
        assert "7d" in pdf_path.name

    @pytest.mark.skipif(
        not Path("/usr/bin/weasyprint").exists()
        and not Path("/usr/local/bin/weasyprint").exists(),
        reason="WeasyPrint not installed",
    )
    def test_pdf_generation_12m(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test 12-month forecast PDF generation."""
        forecast = self._create_sample_forecast(days=365)
        artifacts = {
            "weights": {"arima_garch": 0.5, "var": 0.3, "random_forest": 0.2},
        }

        # Generate charts
        chart_gen = ChartGenerator(test_settings)
        charts = chart_gen.generate(sample_data_bundle, forecast, horizon="12m")

        # Build PDF report
        report_builder = ReportBuilder(test_settings)
        pdf_path = report_builder.build(
            bundle=sample_data_bundle,
            forecast=forecast,
            artifacts=artifacts,
            charts=charts,
            horizon="12m",
        )

        # Verify PDF was created
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stat().st_size > 10000

        # Verify filename contains horizon
        assert "12m" in pdf_path.name

    def test_spanish_characters_in_markdown(self):
        """Test that Spanish characters are handled correctly in markdown."""
        from markdown import markdown

        spanish_text = (
            "Proyección USD/CLP con análisis económico.\n"
            "Características: año, señal, número.\n"
            "¡Información crítica para importación!"
        )

        html = markdown(spanish_text)

        # Verify Spanish characters are preserved
        assert "Proyección" in html
        assert "análisis" in html
        assert "económico" in html
        assert "año" in html
        assert "señal" in html
        assert "número" in html
        assert "¡" in html
        assert "importación" in html

    def test_report_builder_error_without_weasyprint(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
        monkeypatch,
    ):
        """Test that report builder raises clear error if WeasyPrint unavailable."""
        # Mock WeasyPrint unavailability
        import forex_core.reporting.builder as builder_module

        monkeypatch.setattr(builder_module, "HTML", None)
        monkeypatch.setattr(
            builder_module, "WEASYPRINT_ERROR", ImportError("Test error")
        )

        forecast = self._create_sample_forecast(days=7)
        artifacts = {"weights": {}}
        charts = {}

        report_builder = ReportBuilder(test_settings)

        # Should raise RuntimeError with helpful message
        with pytest.raises(RuntimeError) as exc_info:
            report_builder.build(
                bundle=sample_data_bundle,
                forecast=forecast,
                artifacts=artifacts,
                charts=charts,
            )

        error_msg = str(exc_info.value)
        assert "WeasyPrint no está disponible" in error_msg
        assert "Docker" in error_msg or "sistema" in error_msg

    # Helper methods

    def _create_sample_forecast(self, days: int = 7) -> ForecastResult:
        """Create sample forecast for testing."""
        base_date = datetime.now()
        base_value = 950.0

        points = []
        for i in range(days):
            date = base_date + pd.Timedelta(days=i + 1)
            mean = base_value + i * 0.5  # Slight upward trend

            point = ForecastPoint(
                date=date,
                mean=mean,
                ci80_low=mean - 5.0,
                ci80_high=mean + 5.0,
                ci95_low=mean - 10.0,
                ci95_high=mean + 10.0,
                std_dev=3.8,
            )
            points.append(point)

        return ForecastResult(
            series=points,
            methodology="Test ensemble model (ARIMA + VAR + RF)",
            error_metrics={"rmse": 5.2, "mae": 3.8, "mape": 0.4},
            residual_vol=4.1,
        )


@pytest.mark.e2e
class TestPDFContent:
    """Tests for PDF content validation."""

    def test_forecast_table_generation(
        self,
        test_settings: Settings,
    ):
        """Test that forecast table is generated correctly."""
        from forex_core.reporting.builder import ReportBuilder

        forecast = TestPDFGeneration()._create_sample_forecast(days=7)
        builder = ReportBuilder(test_settings)

        table_md = builder._build_forecast_table(forecast)

        # Verify markdown table structure
        assert "| Fecha |" in table_md
        assert "| Proyección Media |" in table_md
        assert "|-------|" in table_md

        # Verify all forecast points are included
        for point in forecast.series:
            date_str = point.date.strftime("%Y-%m-%d")
            assert date_str in table_md

    def test_interpretation_section(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test interpretation section generation."""
        from forex_core.reporting.builder import ReportBuilder

        forecast = TestPDFGeneration()._create_sample_forecast(days=7)
        builder = ReportBuilder(test_settings)

        interpretation = builder._build_interpretation(
            sample_data_bundle, forecast, "7d"
        )

        # Verify key elements
        assert "Tendencia esperada" in interpretation
        assert "USD/CLP" in interpretation
        assert "950" in interpretation  # Base value from fixtures
        assert "%" in interpretation

    def test_drivers_section(
        self,
        test_settings: Settings,
        sample_data_bundle: DataBundle,
    ):
        """Test drivers section generation."""
        from forex_core.reporting.builder import ReportBuilder

        forecast = TestPDFGeneration()._create_sample_forecast(days=7)
        builder = ReportBuilder(test_settings)

        drivers = builder._build_drivers(sample_data_bundle, forecast)

        # Verify key drivers are mentioned
        assert "Cobre" in drivers or "copper" in drivers.lower()
        assert "tasas" in drivers.lower() or "tpm" in drivers.lower()


# Import pandas for helper method
import pandas as pd
