"""
Chart Generation Module for USD/CLP Forecasting System.

This module provides chart generation capabilities using matplotlib and seaborn
for visualizing forecast data and historical series.

Dependencies:
    - matplotlib
    - seaborn
    - pandas

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ..config.base import Settings
from ..data.models import ForecastResult
from ..data.loader import DataBundle

matplotlib.use("Agg")


class ChartGenerator:
    """
    Generates charts for forex forecasting reports.

    This class creates publication-ready charts with:
    - Historical data visualization
    - Forecast projections with confidence intervals
    - Spanish labels and formatting
    - High-resolution output (200 DPI)

    Attributes:
        settings: System configuration settings
        chart_dir: Directory for saving chart files
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the chart generator.

        Args:
            settings: System configuration with chart directory path
        """
        self.settings = settings
        self.chart_dir = Path(settings.output_dir) / "charts"
        self.chart_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid")

    def generate(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str = "7d",
    ) -> Dict[str, Path]:
        """
        Generate all charts for a forecast report.

        Args:
            bundle: Data bundle with historical data
            forecast: Forecast results with predictions and confidence intervals
            horizon: Forecast horizon ("7d" or "12m")

        Returns:
            Dictionary mapping chart names to file paths
        """
        charts = {}

        # Chart 1: Historical + Forecast
        charts["hist_forecast"] = self._generate_hist_forecast_chart(
            bundle, forecast, horizon
        )

        # Chart 2: Forecast with confidence bands
        charts["forecast_bands"] = self._generate_forecast_bands_chart(
            forecast, horizon
        )

        return charts

    def _generate_hist_forecast_chart(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str,
    ) -> Path:
        """
        Generate chart showing historical data and forecast projection.

        Args:
            bundle: Data bundle with historical series
            forecast: Forecast results
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        # Get last 30 days of historical data
        hist = bundle.usdclp_series.tail(30)

        # Build forecast DataFrame
        fc_df = pd.DataFrame(
            {
                "mean": [point.mean for point in forecast.series],
                "ci80_low": [point.ci80_low for point in forecast.series],
                "ci80_high": [point.ci80_high for point in forecast.series],
                "ci95_low": [point.ci95_low for point in forecast.series],
                "ci95_high": [point.ci95_high for point in forecast.series],
            },
            index=[point.date for point in forecast.series],
        )

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot historical data
        hist.plot(ax=ax, label="Histórico 30d", color="#1f77b4", linewidth=2)

        # Plot forecast mean
        fc_df["mean"].plot(
            ax=ax, label="Proyección media", color="#d62728", linewidth=2
        )

        # Plot confidence intervals
        ax.fill_between(
            fc_df.index,
            fc_df["ci80_low"],
            fc_df["ci80_high"],
            color="#ff9896",
            alpha=0.3,
            label="IC 80%",
        )
        ax.fill_between(
            fc_df.index,
            fc_df["ci95_low"],
            fc_df["ci95_high"],
            color="#c5b0d5",
            alpha=0.2,
            label="IC 95%",
        )

        # Formatting
        title = f"USD/CLP - Histórico reciente + Proyección {horizon}"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("CLP por USD", fontsize=12)
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Save chart
        chart_path = self.chart_dir / f"chart_hist_forecast_{horizon}.png"
        fig.tight_layout()
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    def _generate_forecast_bands_chart(
        self,
        forecast: ForecastResult,
        horizon: str,
    ) -> Path:
        """
        Generate chart showing forecast with confidence bands only.

        Args:
            forecast: Forecast results
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        # Build forecast DataFrame
        fc_df = pd.DataFrame(
            {
                "mean": [point.mean for point in forecast.series],
                "ci80_low": [point.ci80_low for point in forecast.series],
                "ci80_high": [point.ci80_high for point in forecast.series],
                "ci95_low": [point.ci95_low for point in forecast.series],
                "ci95_high": [point.ci95_high for point in forecast.series],
            },
            index=[point.date for point in forecast.series],
        )

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 4))

        # Plot forecast mean
        fc_df["mean"].plot(
            ax=ax, color="#2ca02c", label="Media proyectada", linewidth=2
        )

        # Plot confidence intervals
        ax.fill_between(
            fc_df.index,
            fc_df["ci80_low"],
            fc_df["ci80_high"],
            alpha=0.3,
            color="#98df8a",
            label="IC 80%",
        )
        ax.fill_between(
            fc_df.index,
            fc_df["ci95_low"],
            fc_df["ci95_high"],
            alpha=0.2,
            color="#c7e9c0",
            label="IC 95%",
        )

        # Formatting
        title = f"USD/CLP - Intervalos de confianza {horizon}"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("CLP por USD", fontsize=12)
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Save chart
        chart_path = self.chart_dir / f"chart_forecast_bands_{horizon}.png"
        fig.tight_layout()
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    @staticmethod
    def image_to_base64(path: Path) -> str:
        """
        Convert image file to base64 encoded data URI.

        Args:
            path: Path to image file

        Returns:
            Base64 encoded data URI string
        """
        with path.open("rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def charts_to_base64(self, chart_paths: Dict[str, Path]) -> List[str]:
        """
        Convert multiple chart files to base64 data URIs.

        Args:
            chart_paths: Dictionary mapping chart names to paths

        Returns:
            List of base64 encoded data URIs
        """
        return [self.image_to_base64(path) for path in chart_paths.values()]
