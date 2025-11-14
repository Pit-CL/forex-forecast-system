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


# Horizon-specific lookback periods for charts
CHART_HIST_LOOKBACK = {
    "7d": 30,
    "15d": 60,
    "30d": 90,
    "90d": 180,
    "12m": 365,
}

CHART_TECH_LOOKBACK = {
    "7d": 60,
    "15d": 90,
    "30d": 120,
    "90d": 240,
    "12m": 365,
}

CHART_MACRO_LOOKBACK = {
    "7d": 90,
    "15d": 120,
    "30d": 180,
    "90d": 365,
    "12m": 730,
}

CHART_REGIME_LOOKBACK = {
    "7d": 30,
    "15d": 45,
    "30d": 60,
    "90d": 90,
    "12m": 180,
}


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

    def _format_date_axis(self, ax, date_format='%d-%b', rotation=45, max_ticks=8):
        """
        Formato consistente de fechas en eje X.

        Args:
            ax: Matplotlib axis
            date_format: Formato de fecha (ej: '%d-%b' -> '15-Nov')
            rotation: Angulo de rotacion de labels
            max_ticks: Maximo numero de ticks a mostrar
        """
        from matplotlib.dates import DateFormatter, AutoDateLocator
        from matplotlib.ticker import MaxNLocator

        formatter = DateFormatter(date_format)
        locator = AutoDateLocator(maxticks=max_ticks)
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_major_locator(locator)
        plt.setp(ax.xaxis.get_majorticklabels(),
                 rotation=rotation,
                 ha='right',
                 fontsize=9)

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

        # Chart 1A: Historical Overview (context, no bands)
        charts["hist_overview"] = self._generate_hist_forecast_overview(
            bundle, forecast, horizon
        )

        # Chart 1B: Tactical Zoom (last 5 days + forecast WITH bands)
        charts["tactical_zoom"] = self._generate_tactical_zoom_chart(
            bundle, forecast, horizon
        )

        # Chart 2: Forecast with confidence bands
        charts["forecast_bands"] = self._generate_forecast_bands_chart(
            forecast, horizon
        )

        # Chart 3: Technical Indicators Panel
        charts["technical_panel"] = self._generate_technical_panel(bundle, horizon)

        # Chart 4: Correlation Matrix
        charts["correlation"] = self._generate_correlation_matrix(bundle, horizon)

        # Chart 5: Macro Drivers Dashboard
        charts["macro_drivers"] = self._generate_macro_dashboard(bundle, horizon)

        # Chart 6: Risk Regime Visualization
        charts["risk_regime"] = self._generate_regime_chart(bundle, horizon)

        return charts

    def _generate_hist_forecast_overview(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str,
    ) -> Path:
        """
        Generate overview chart showing full historical context + forecast (NO confidence bands).

        Args:
            bundle: Data bundle with historical series
            forecast: Forecast results
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        # Get historical data based on horizon
        hist = bundle.usdclp_series.tail(CHART_HIST_LOOKBACK.get(horizon, 30))

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

        # Plot historical data (context based on horizon)
        lookback_days = CHART_HIST_LOOKBACK.get(horizon, 30)
        ax.plot(hist.index, hist.values, label=f"Histórico {lookback_days}d", color="#1f77b4", linewidth=2)

        # Plot forecast mean
        ax.plot(fc_df.index, fc_df["mean"].values, label="Proyección media", color="#d62728", linewidth=2.5)

        # Formatting
        title = f"USD/CLP - Contexto Histórico + Proyección {horizon}"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("CLP por USD", fontsize=12)
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Format date axis to prevent overlapping labels
        self._format_date_axis(ax, date_format='%Y-%m-%d', rotation=45, max_ticks=10)

        # Save chart
        chart_path = self.chart_dir / f"chart_hist_overview_{horizon}.png"
        fig.tight_layout()
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    def _generate_tactical_zoom_chart(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str,
    ) -> Path:
        """
        Generate tactical zoom chart showing last 5 days + forecast WITH confidence bands.

        Args:
            bundle: Data bundle with historical series
            forecast: Forecast results
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        # Get last 5 days only for tactical zoom
        hist = bundle.usdclp_series.tail(5)

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

        # Plot historical data (last 5 days)
        ax.plot(hist.index, hist.values, label="Últimos 5d", color="#1f77b4", linewidth=2, marker='o', markersize=4)

        # Plot confidence intervals with HIGH visibility
        ax.fill_between(
            fc_df.index,
            fc_df["ci95_low"].values,
            fc_df["ci95_high"].values,
            color="#8B00FF",
            alpha=0.5,
            label="IC 95%",
            zorder=2,
        )
        ax.fill_between(
            fc_df.index,
            fc_df["ci80_low"].values,
            fc_df["ci80_high"].values,
            color="#FF8C00",
            alpha=0.65,
            label="IC 80%",
            zorder=3,
        )

        # Plot forecast mean
        ax.plot(fc_df.index, fc_df["mean"].values, label="Proyección media", color="#d62728", linewidth=2.5, marker='o', markersize=4)

        # Formatting
        title = f"USD/CLP - Zoom Táctico (Últimos 5d + Proyección {horizon})"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("CLP por USD", fontsize=12)
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Tight Y-axis for visibility
        all_values = list(hist.values) + list(fc_df["ci95_low"].values) + list(fc_df["ci95_high"].values)
        y_min = min(all_values)
        y_max = max(all_values)
        y_padding = (y_max - y_min) * 0.1  # 10% padding
        ax.set_ylim(y_min - y_padding, y_max + y_padding)

        # Format date axis to prevent overlapping labels
        self._format_date_axis(ax, date_format='%Y-%m-%d', rotation=45, max_ticks=8)

        # Save chart
        chart_path = self.chart_dir / f"chart_tactical_zoom_{horizon}.png"
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

        # Plot confidence intervals FIRST (so they appear behind)
        ax.fill_between(
            fc_df.index,
            fc_df["ci95_low"],
            fc_df["ci95_high"],
            color="#8B00FF",  # Violet for 95% CI (DarkViolet)
            alpha=0.50,  # Increased from 0.20 for visibility
            edgecolor="none",
            label="IC 95%",
            zorder=2,
        )
        ax.fill_between(
            fc_df.index,
            fc_df["ci80_low"],
            fc_df["ci80_high"],
            color="#FF8C00",  # Orange for 80% CI (DarkOrange)
            alpha=0.65,  # Increased from 0.40 for visibility
            edgecolor="none",
            label="IC 80%",
            zorder=3,
        )

        # Plot forecast mean (on top of bands)
        fc_df["mean"].plot(
            ax=ax, color="#2ca02c", label="Media proyectada", linewidth=2, zorder=4
        )

        # Formatting
        title = f"USD/CLP - Intervalos de confianza {horizon}"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylabel("CLP por USD", fontsize=12)
        ax.legend(loc="best", fontsize=10)
        ax.grid(True, alpha=0.3, zorder=1)

        # Format date axis to prevent overlapping labels
        self._format_date_axis(ax, date_format='%Y-%m-%d', rotation=45, max_ticks=8)

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

    def _generate_technical_panel(
        self,
        bundle: DataBundle,
        horizon: str,
    ) -> Path:
        """
        Generate technical indicators panel with RSI, MACD, and Bollinger Bands.

        Args:
            bundle: Data bundle with historical series
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        from ..analysis.technical import compute_technicals

        # Compute technical indicators
        technicals = compute_technicals(bundle.usdclp_series)
        frame = technicals["frame"].tail(CHART_TECH_LOOKBACK.get(horizon, 60))

        # Create figure with 3 subplots
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

        # Subplot 1: Price with Bollinger Bands
        ax1 = axes[0]
        ax1.plot(frame.index, frame["close"], label="USD/CLP", color="#1f77b4", linewidth=2)
        ax1.plot(frame.index, frame["ma_20"], label="MA 20", color="#2ca02c", linewidth=1.5, linestyle="--")
        ax1.fill_between(
            frame.index,
            frame["bb_lower"],
            frame["bb_upper"],
            alpha=0.2,
            color="#98df8a",
            label="Bollinger Bands (±2σ)",
        )
        ax1.set_ylabel("CLP por USD", fontsize=11)
        lookback_days = CHART_TECH_LOOKBACK.get(horizon, 60)
        ax1.set_title(f"Análisis Técnico USD/CLP ({lookback_days} días)", fontsize=13, fontweight="bold")
        ax1.legend(loc="best", fontsize=9)
        ax1.grid(True, alpha=0.3)

        # Subplot 2: RSI
        ax2 = axes[1]
        ax2.plot(frame.index, frame["rsi_14"], color="#d62728", linewidth=2)
        ax2.axhline(y=70, color="red", linestyle="--", linewidth=1, alpha=0.7, label="Sobrecompra")
        ax2.axhline(y=30, color="green", linestyle="--", linewidth=1, alpha=0.7, label="Sobreventa")
        ax2.axhline(y=50, color="gray", linestyle=":", linewidth=1, alpha=0.5)
        ax2.fill_between(frame.index, 30, 70, alpha=0.1, color="gray")
        ax2.set_ylabel("RSI (14)", fontsize=11)
        ax2.set_ylim(0, 100)
        ax2.legend(loc="best", fontsize=9)
        ax2.grid(True, alpha=0.3)

        # Subplot 3: MACD
        ax3 = axes[2]
        macd_hist = frame["macd"] - frame["macd_signal"]
        colors = ["green" if x > 0 else "red" for x in macd_hist]
        ax3.bar(frame.index, macd_hist, color=colors, alpha=0.5, label="MACD Histogram")
        ax3.plot(frame.index, frame["macd"], label="MACD", color="#ff7f0e", linewidth=2)
        ax3.plot(frame.index, frame["macd_signal"], label="Signal", color="#9467bd", linewidth=2)
        ax3.axhline(y=0, color="black", linestyle="-", linewidth=0.8, alpha=0.5)
        ax3.set_ylabel("MACD", fontsize=11)
        ax3.set_xlabel("Fecha", fontsize=11)
        ax3.legend(loc="best", fontsize=9)
        ax3.grid(True, alpha=0.3)

        # Aplicar formato de fechas al eje X compartido (solo en el ultimo subplot)
        self._format_date_axis(ax3, date_format='%d-%b', rotation=45, max_ticks=8)

        # Caption con fuente
        fig.text(0.5, 0.01,
                 'Fuente: Elaboracion propia con datos de Mindicador.cl y Alpha Vantage',
                 ha='center', fontsize=9, style='italic', color='gray')

        # Save chart
        chart_path = self.chart_dir / f"chart_technical_panel_{horizon}.png"
        fig.tight_layout(rect=[0, 0.02, 1, 1])  # Ajustar para caption
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    def _generate_correlation_matrix(
        self,
        bundle: DataBundle,
        horizon: str,
    ) -> Path:
        """
        Generate correlation matrix heatmap for USD/CLP vs key drivers.

        Args:
            bundle: Data bundle with historical series
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        import numpy as np

        # Build correlation dataframe - only include series that exist
        # Start with required series - NORMALIZE DATES TO REMOVE TIME/TZ
        series_list = []
        series_names = []

        # USD/CLP (required)
        usdclp_normalized = bundle.usdclp_series.copy()
        usdclp_normalized.index = pd.to_datetime(usdclp_normalized.index.date)
        series_list.append(usdclp_normalized)
        series_names.append("USD/CLP")

        # Copper (required)
        copper_normalized = bundle.copper_series.copy()
        copper_normalized.index = pd.to_datetime(copper_normalized.index.date)
        series_list.append(copper_normalized)
        series_names.append("Cobre")

        # Add optional series only if they exist and have data - NORMALIZE DATES
        if hasattr(bundle, "dxy_series") and bundle.dxy_series is not None and len(bundle.dxy_series) > 0:
            dxy_normalized = bundle.dxy_series.copy()
            dxy_normalized.index = pd.to_datetime(dxy_normalized.index.date)
            series_list.append(dxy_normalized)
            series_names.append("DXY")

        if hasattr(bundle, "vix_series") and bundle.vix_series is not None and len(bundle.vix_series) > 0:
            vix_normalized = bundle.vix_series.copy()
            vix_normalized.index = pd.to_datetime(vix_normalized.index.date)
            series_list.append(vix_normalized)
            series_names.append("VIX")

        if hasattr(bundle, "eem_series") and bundle.eem_series is not None and len(bundle.eem_series) > 0:
            eem_normalized = bundle.eem_series.copy()
            eem_normalized.index = pd.to_datetime(eem_normalized.index.date)
            series_list.append(eem_normalized)
            series_names.append("EEM")

        # Concatenate series with INNER join to keep only common dates (now normalized)
        corr_data = pd.concat(series_list, axis=1, keys=series_names, join='inner')

        # Drop any remaining rows with NaN values (should be few or none with inner join)
        corr_data = corr_data.dropna()

        # Check if we have enough data (minimum 5 observations for statistical reliability)
        MIN_CORRELATION_OBSERVATIONS = 5
        if len(corr_data) < MIN_CORRELATION_OBSERVATIONS:
            from forex_core.utils.logging import logger
            logger.warning(
                f"Insufficient data for correlation matrix: {len(corr_data)} rows "
                f"(need at least {MIN_CORRELATION_OBSERVATIONS}). Creating NaN matrix."
            )
            # Create empty correlation matrix as fallback
            corr_matrix = pd.DataFrame(
                np.nan,
                index=series_names,
                columns=series_names
            )
        else:
            # Compute returns for correlation
            corr_returns = corr_data.pct_change(fill_method=None).dropna()

            # Compute correlation matrix
            corr_matrix = corr_returns.corr()

        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))

        # Custom colormap - diverging blue to red
        cmap = sns.diverging_palette(250, 10, as_cmap=True)

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".2f",
            cmap=cmap,
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8, "label": "Correlación"},
            ax=ax,
            vmin=-1,
            vmax=1,
        )

        ax.set_title(
            "Matriz de Correlaciones - Retornos Diarios (60 días)",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )

        # Rotate labels
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

        # Caption con fuente
        fig.text(0.5, 0.01,
                 'Fuente: Elaboracion propia con datos de Yahoo Finance (retornos diarios)',
                 ha='center', fontsize=9, style='italic', color='gray')

        # Save chart
        chart_path = self.chart_dir / f"chart_correlation_{horizon}.png"
        fig.tight_layout(rect=[0, 0.02, 1, 1])  # Ajustar para caption
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    def _generate_macro_dashboard(
        self,
        bundle: DataBundle,
        horizon: str,
    ) -> Path:
        """
        Generate macro drivers dashboard showing key economic indicators.

        Args:
            bundle: Data bundle with indicators
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Get lookback period based on horizon
        lookback = CHART_MACRO_LOOKBACK.get(horizon, 90)

        # Subplot 1: USD/CLP vs Copper
        ax1 = axes[0, 0]
        ax1_twin = ax1.twinx()

        usd_recent = bundle.usdclp_series.tail(lookback)
        copper_recent = bundle.copper_series.tail(lookback)

        ax1.plot(usd_recent.index, usd_recent.values, color="#1f77b4", linewidth=2, label="USD/CLP")
        ax1_twin.plot(copper_recent.index, copper_recent.values, color="#d62728", linewidth=2, label="Cobre", linestyle="--")

        ax1.set_ylabel("USD/CLP", color="#1f77b4", fontsize=10)
        ax1_twin.set_ylabel("Cobre (USD/lb)", color="#d62728", fontsize=10)
        ax1.set_title("USD/CLP vs Precio del Cobre", fontsize=12, fontweight="bold")
        ax1.tick_params(axis="y", labelcolor="#1f77b4")
        ax1_twin.tick_params(axis="y", labelcolor="#d62728")
        ax1.grid(True, alpha=0.3)
        self._format_date_axis(ax1, date_format='%d-%b', rotation=45, max_ticks=6)

        # Subplot 2: Interest Rate Differential
        ax2 = axes[0, 1]
        tpm_recent = bundle.tpm_series.tail(lookback)

        # Get Fed Funds if available
        if hasattr(bundle, "fed_series"):
            fed_recent = bundle.fed_series.tail(lookback).reindex(tpm_recent.index, method="ffill")
            diff = tpm_recent - fed_recent
            ax2.plot(tpm_recent.index, diff, color="#2ca02c", linewidth=2, marker="o", markersize=3)
            ax2.axhline(y=0, color="black", linestyle="--", linewidth=1, alpha=0.5)
            ax2.set_ylabel("Diferencial (pp)", fontsize=10)
            ax2.set_title("Diferencial TPM - Fed Funds", fontsize=12, fontweight="bold")
        else:
            ax2.plot(tpm_recent.index, tpm_recent, color="#2ca02c", linewidth=2, marker="o", markersize=3)
            ax2.set_ylabel("TPM (%)", fontsize=10)
            ax2.set_title("Tasa de Política Monetaria (TPM)", fontsize=12, fontweight="bold")

        ax2.grid(True, alpha=0.3)
        self._format_date_axis(ax2, date_format='%d-%b', rotation=45, max_ticks=6)

        # Subplot 3: DXY Index
        ax3 = axes[1, 0]
        if hasattr(bundle, "dxy_series"):
            dxy_recent = bundle.dxy_series.tail(lookback)
            ax3.plot(dxy_recent.index, dxy_recent.values, color="#ff7f0e", linewidth=2)
            ax3.fill_between(dxy_recent.index, dxy_recent.values, alpha=0.2, color="#ff7f0e")
            ax3.set_ylabel("DXY Index", fontsize=10)
            ax3.set_title("Índice Dólar (DXY)", fontsize=12, fontweight="bold")
        else:
            ax3.text(0.5, 0.5, "DXY no disponible", ha="center", va="center", fontsize=12)
            ax3.set_title("Índice Dólar (DXY)", fontsize=12, fontweight="bold")

        ax3.grid(True, alpha=0.3)
        ax3.set_xlabel("Fecha", fontsize=10)
        self._format_date_axis(ax3, date_format='%d-%b', rotation=45, max_ticks=6)

        # Subplot 4: Inflation
        ax4 = axes[1, 1]
        ipc_recent = bundle.inflation_series.tail(lookback)
        ax4.bar(ipc_recent.index, ipc_recent.values, color="#9467bd", alpha=0.7, width=20)
        ax4.axhline(y=0, color="black", linestyle="-", linewidth=1)
        ax4.set_ylabel("IPC Mensual (%)", fontsize=10)
        ax4.set_xlabel("Fecha", fontsize=10)
        ax4.set_title("Inflación Chile (IPC)", fontsize=12, fontweight="bold")
        ax4.grid(True, alpha=0.3, axis="y")
        self._format_date_axis(ax4, date_format='%d-%b', rotation=45, max_ticks=6)

        # Overall title
        fig.suptitle("Dashboard de Drivers Macroeconómicos", fontsize=16, fontweight="bold", y=0.995)

        # Caption con fuente
        fig.text(0.5, 0.01,
                 'Fuente: Elaboracion propia con datos de Mindicador.cl (BCCh), Yahoo Finance',
                 ha='center', fontsize=9, style='italic', color='gray')

        # Save chart
        chart_path = self.chart_dir / f"chart_macro_dashboard_{horizon}.png"
        fig.tight_layout(rect=[0, 0.02, 1, 0.99])  # Ajustar para caption y titulo
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path

    def _generate_regime_chart(
        self,
        bundle: DataBundle,
        horizon: str,
    ) -> Path:
        """
        Generate risk regime visualization chart.

        Args:
            bundle: Data bundle with macro series
            horizon: Forecast horizon for labeling

        Returns:
            Path to saved chart file
        """
        from ..analysis.macro import compute_risk_gauge

        # Compute current regime
        try:
            gauge = compute_risk_gauge(bundle)
        except (KeyError, AttributeError):
            # If data not available, create placeholder
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(
                0.5, 0.5,
                "Datos insuficientes para análisis de régimen\n(Requiere: DXY, VIX, EEM)",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.set_title("Régimen de Riesgo de Mercado", fontsize=14, fontweight="bold")
            ax.axis("off")

            chart_path = self.chart_dir / f"chart_risk_regime_{horizon}.png"
            fig.tight_layout()
            fig.savefig(chart_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            return chart_path

        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Get lookback period based on horizon
        lookback = CHART_REGIME_LOOKBACK.get(horizon, 30)
        dxy_recent = bundle.dxy_series.tail(lookback)
        vix_recent = bundle.vix_series.tail(lookback)
        eem_recent = bundle.eem_series.tail(lookback)

        # Subplot 1: DXY
        ax1 = axes[0, 0]
        ax1.plot(dxy_recent.index, dxy_recent.values, color="#1f77b4", linewidth=2)
        ax1.set_title(f"DXY: {gauge.dxy_change:+.2f}%", fontsize=12, fontweight="bold")
        ax1.set_ylabel("DXY Index", fontsize=10)
        ax1.grid(True, alpha=0.3)
        self._format_date_axis(ax1, date_format='%d-%b', rotation=45, max_ticks=5)

        # Color background based on change
        if gauge.dxy_change < 0:
            ax1.set_facecolor("#e8f5e9")  # Green tint
        else:
            ax1.set_facecolor("#ffebee")  # Red tint

        # Subplot 2: VIX
        ax2 = axes[0, 1]
        ax2.plot(vix_recent.index, vix_recent.values, color="#d62728", linewidth=2)
        ax2.set_title(f"VIX: {gauge.vix_change:+.2f}%", fontsize=12, fontweight="bold")
        ax2.set_ylabel("VIX Index", fontsize=10)
        ax2.grid(True, alpha=0.3)
        self._format_date_axis(ax2, date_format='%d-%b', rotation=45, max_ticks=5)

        if gauge.vix_change < 0:
            ax2.set_facecolor("#e8f5e9")
        else:
            ax2.set_facecolor("#ffebee")

        # Subplot 3: EEM
        ax3 = axes[1, 0]
        ax3.plot(eem_recent.index, eem_recent.values, color="#2ca02c", linewidth=2)
        ax3.set_title(f"EEM: {gauge.eem_change:+.2f}%", fontsize=12, fontweight="bold")
        ax3.set_ylabel("EEM ETF", fontsize=10)
        ax3.set_xlabel("Fecha", fontsize=10)
        ax3.grid(True, alpha=0.3)
        self._format_date_axis(ax3, date_format='%d-%b', rotation=45, max_ticks=5)

        if gauge.eem_change > 0:
            ax3.set_facecolor("#e8f5e9")
        else:
            ax3.set_facecolor("#ffebee")

        # Subplot 4: Regime Summary
        ax4 = axes[1, 1]
        ax4.axis("off")

        # Determine color based on regime
        if gauge.regime == "Risk-on":
            regime_color = "#4caf50"  # Green
            emoji = "📈"
        elif gauge.regime == "Risk-off":
            regime_color = "#f44336"  # Red
            emoji = "📉"
        else:
            regime_color = "#ff9800"  # Orange
            emoji = "↔️"

        # Display regime
        ax4.text(
            0.5, 0.7,
            f"{emoji} {gauge.regime}",
            ha="center",
            va="center",
            fontsize=32,
            fontweight="bold",
            color=regime_color,
        )

        # Interpretation
        if gauge.regime == "Risk-on":
            interpretation = "Apetito por riesgo alto\nFavorece a mercados emergentes\nPositivo para CLP"
        elif gauge.regime == "Risk-off":
            interpretation = "Aversión al riesgo\nFlujos hacia activos seguros\nPresión sobre CLP"
        else:
            interpretation = "Señales mixtas\nMercado en transición\nNeutral para CLP"

        ax4.text(
            0.5, 0.3,
            interpretation,
            ha="center",
            va="center",
            fontsize=12,
            style="italic",
        )

        # Overall title
        fig.suptitle("Régimen de Riesgo de Mercado (5 días)", fontsize=16, fontweight="bold")

        # Caption con fuente
        fig.text(0.5, 0.01,
                 'Fuente: Elaboracion propia con datos de Yahoo Finance (DXY, VIX, EEM)',
                 ha='center', fontsize=9, style='italic', color='gray')

        # Save chart
        chart_path = self.chart_dir / f"chart_risk_regime_{horizon}.png"
        fig.tight_layout(rect=[0, 0.02, 1, 0.98])  # Ajustar para caption y titulo
        fig.savefig(chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        return chart_path
