"""
PDF Report Builder for USD/CLP Forecasting System.

This module provides comprehensive report generation capabilities including:
- Markdown to HTML conversion
- PDF rendering with WeasyPrint
- Multi-section report assembly
- Source citation management

Dependencies:
    - weasyprint
    - jinja2
    - markdown

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown

from ..config.base import Settings
from ..data.models import ForecastResult
from ..data.loader import DataBundle

try:
    from weasyprint import HTML

    WEASYPRINT_ERROR = None
except Exception as exc:
    HTML = None
    WEASYPRINT_ERROR = exc


class ReportBuilder:
    """
    Builds comprehensive PDF reports for forex forecasts.

    This class assembles multi-section reports with:
    - Executive summary and interpretation
    - Forecast tables and charts
    - Technical analysis and risk assessment
    - Methodology and source citations

    Attributes:
        settings: System configuration
        templates_dir: Directory containing Jinja2 templates
        template: Main report template
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the report builder.

        Args:
            settings: System configuration with output paths and timezone
        """
        self.settings = settings

        # Setup Jinja2 environment
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.template = self.env.get_template("report.html.j2")

    def build(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        artifacts: Dict,
        charts: Dict[str, Path],
        horizon: str = "7d",
    ) -> Path:
        """
        Build complete PDF report.

        Args:
            bundle: Data bundle with historical data and indicators
            forecast: Forecast results with predictions
            artifacts: Forecast artifacts (model metrics, weights, etc.)
            charts: Dictionary mapping chart names to file paths
            horizon: Forecast horizon for labeling

        Returns:
            Path to generated PDF file
        """
        # Convert charts to base64
        from .charting import ChartGenerator

        chart_imgs = [ChartGenerator.image_to_base64(path) for path in charts.values()]

        # Build markdown sections
        markdown_body = self._build_markdown_sections(
            bundle, forecast, artifacts, horizon
        )

        # Convert markdown to HTML
        html_content = markdown(markdown_body, extensions=["tables", "fenced_code"])

        # Render with template
        tz = ZoneInfo(self.settings.report_timezone)
        html_body = self.template.render(
            body=html_content,
            charts=chart_imgs,
            generated_at=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"),
            timezone=self.settings.report_timezone,
        )

        # Write PDF
        pdf_path = self._write_pdf(html_body, horizon)

        return pdf_path

    def _build_markdown_sections(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        artifacts: Dict,
        horizon: str,
    ) -> str:
        """
        Build markdown content for all report sections.

        Args:
            bundle: Data bundle
            forecast: Forecast results
            artifacts: Forecast artifacts
            horizon: Forecast horizon

        Returns:
            Complete markdown document
        """
        sections = []

        # Title
        if horizon == "7d":
            title = "# Proyección USD/CLP (7 días)"
        elif horizon == "12m":
            title = "# Proyección USD/CLP (12 meses)"
        else:
            title = f"# Proyección USD/CLP ({horizon})"
        sections.append(title)

        # Forecast table
        sections.append("## Proyección")
        sections.append(self._build_forecast_table(forecast))

        # Executive summary
        sections.append("## Interpretación Ejecutiva")
        sections.append(self._build_interpretation(bundle, forecast, horizon))

        # Key drivers
        sections.append("## Drivers Clave")
        sections.append(self._build_drivers(bundle, forecast))

        # Methodology
        sections.append("## Razonamiento y Metodología")
        sections.append(self._build_methodology(artifacts))

        # Conclusion
        sections.append("## Conclusión Técnica")
        sections.append(self._build_conclusion(bundle, forecast))

        # Sources
        sections.append("## Fuentes y Validación")
        sections.append(bundle.sources.as_markdown())

        return "\n\n".join(sections)

    def _build_forecast_table(self, forecast: ForecastResult) -> str:
        """Build markdown table with forecast points."""
        rows = [
            "| Fecha | Proyección Media | IC 80% Inferior | IC 80% Superior | IC 95% Inferior | IC 95% Superior |",
            "|-------|------------------|-----------------|-----------------|-----------------|-----------------|",
        ]

        for point in forecast.series:
            row = (
                f"| {point.date.strftime('%Y-%m-%d')} "
                f"| {point.mean:.2f} "
                f"| {point.ci80_low:.2f} "
                f"| {point.ci80_high:.2f} "
                f"| {point.ci95_low:.2f} "
                f"| {point.ci95_high:.2f} |"
            )
            rows.append(row)

        return "\n".join(rows)

    def _build_interpretation(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str,
    ) -> str:
        """Build executive interpretation section."""
        if not forecast.series:
            return "Sin proyección disponible."

        spot = bundle.indicators.get("usdclp_spot")
        if not spot:
            return "Datos insuficientes para interpretación."

        last_point = forecast.series[-1]
        move_pct = ((last_point.mean / spot.value) - 1) * 100

        if move_pct > 0.5:
            trend = "Alcista"
        elif move_pct < -0.5:
            trend = "Bajista"
        else:
            trend = "Lateral"

        interpretation = (
            f"Tendencia esperada: **{trend}** ({move_pct:+.2f}%). "
            f"El escenario central proyecta USD/CLP desde {spot.value:.1f} "
            f"hacia {last_point.mean:.1f} CLP en {horizon}, "
            f"con banda prudente 95% [{last_point.ci95_low:.1f}, {last_point.ci95_high:.1f}]. "
            f"Importadores: considerar coberturas escalonadas aprovechando retrocesos."
        )

        return interpretation

    def _build_drivers(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
    ) -> str:
        """Build key drivers section."""
        drivers = []

        # Copper
        copper = bundle.indicators.get("copper")
        if copper:
            drivers.append(
                f"- **Cobre**: {copper.value:.2f} USD/lb - Soporte estructural al CLP"
            )

        # TPM
        tpm = bundle.indicators.get("tpm")
        fed_target = bundle.indicators.get("fed_target")
        if tpm and fed_target:
            diff = tpm.value - fed_target.value
            drivers.append(
                f"- **Diferencial de tasas**: TPM-Fed = {diff:.2f} pp - Carry para pesos"
            )

        # DXY
        dxy = bundle.indicators.get("dxy")
        if dxy:
            drivers.append(f"- **Dólar global (DXY)**: {dxy.value:.2f} - Régimen USD")

        # IPC
        ipc = bundle.indicators.get("ipc")
        if ipc:
            drivers.append(
                f"- **Inflación chilena (IPC)**: {ipc.value:.2f}% - Guidance BCCh"
            )

        if not drivers:
            return "Drivers clave no disponibles en este reporte."

        return "\n".join(drivers)

    def _build_methodology(self, artifacts: Dict) -> str:
        """Build methodology section."""
        weights = artifacts.get("weights", {})
        if weights:
            weights_str = ", ".join(f"{k}: {v:.2f}" for k, v in weights.items())
            text = (
                f"Tipo de razonamiento: **Pragmático** (ensemble de modelos complementarios). "
                f"Se combinan ARIMA + VAR + RandomForest con pesos: {weights_str}. "
                f"Intervalos de confianza mediante simulación Monte Carlo de residuales."
            )
        else:
            text = (
                "Modelos estadísticos combinados (ARIMA, VAR, RandomForest) con "
                "ponderación por desempeño histórico. Intervalos de confianza calculados "
                "mediante simulación Monte Carlo."
            )

        return text

    def _build_conclusion(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
    ) -> str:
        """Build conclusion section."""
        if not forecast.series:
            return "Conclusión no disponible."

        spot = bundle.indicators.get("usdclp_spot")
        if not spot:
            return "Datos insuficientes para conclusión."

        last_point = forecast.series[-1]
        min_point = min(forecast.series, key=lambda p: p.mean)

        conclusion = (
            f"El escenario central proyecta USD/CLP desde {spot.value:.1f} "
            f"hacia {last_point.mean:.1f} CLP, con banda prudente 95% "
            f"[{last_point.ci95_low:.1f}, {last_point.ci95_high:.1f}]. "
            f"Ventana óptima potencial cerca de {min_point.mean:.1f} CLP "
            f"el {min_point.date.strftime('%d-%b')}. "
            f"Triggers de revisión: cierre bajo {last_point.ci95_low:.1f} "
            f"(rompe sesgo) o sobre {last_point.ci95_high:.1f} (shock externo)."
        )

        return conclusion

    def _write_pdf(self, html_body: str, horizon: str) -> Path:
        """
        Write HTML to PDF file using WeasyPrint.

        Args:
            html_body: Rendered HTML content
            horizon: Forecast horizon for filename

        Returns:
            Path to generated PDF

        Raises:
            RuntimeError: If WeasyPrint is not available
        """
        if HTML is None:
            raise RuntimeError(
                f"WeasyPrint no está disponible en este entorno. "
                f"Instala las dependencias del sistema (Cairo, Pango) "
                f"o ejecuta dentro del contenedor Docker. "
                f"Error original: {WEASYPRINT_ERROR}"
            )

        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"usdclp_report_{horizon}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        pdf_path = output_dir / filename

        HTML(string=html_body, base_url=str(output_dir)).write_pdf(str(pdf_path))

        return pdf_path
