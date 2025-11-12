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
        # Convert charts to base64 with explanations
        from .charting import ChartGenerator

        chart_blocks = self._build_chart_blocks(bundle, charts)

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
            chart_blocks=chart_blocks,
            generated_at=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"),
            timezone=self.settings.report_timezone,
        )

        # Write PDF
        pdf_path = self._write_pdf(html_body, horizon)

        return pdf_path

    def _build_chart_blocks(
        self,
        bundle: DataBundle,
        charts: Dict[str, Path],
    ) -> List[Dict[str, str]]:
        """
        Build chart blocks with embedded explanations.

        Args:
            bundle: Data bundle for generating explanations
            charts: Dictionary mapping chart names to file paths

        Returns:
            List of chart blocks, each containing:
            - image: base64 encoded image
            - title: chart title
            - explanation: 2-3 sentence interpretation
        """
        from .charting import ChartGenerator

        blocks = []

        # Chart 1: Historical + Forecast
        if "hist_forecast" in charts:
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["hist_forecast"]),
                "title": "Proyección USD/CLP con Histórico",
                "explanation": (
                    "Evolución histórica de 60 días y proyección futura con intervalos de confianza. "
                    "Las bandas grises representan incertidumbre: banda oscura (80% confianza), "
                    "banda clara (95% confianza). El escenario central aparece en línea azul sólida."
                ),
            })

        # Chart 2: Forecast Bands
        if "forecast_bands" in charts:
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["forecast_bands"]),
                "title": "Bandas de Proyección",
                "explanation": (
                    "Detalle de la proyección mostrando evolución esperada del tipo de cambio. "
                    "La zona sombreada muestra el rango probable de movimiento según el modelo ensemble. "
                    "Importante: mientras más angosta la banda, mayor certeza en la proyección."
                ),
            })

        # Chart 3: Technical Panel
        if "technical_panel" in charts:
            explanation = self._get_technical_panel_explanation(bundle)
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["technical_panel"]),
                "title": "Análisis Técnico USD/CLP",
                "explanation": explanation,
            })

        # Chart 4: Correlation Matrix
        if "correlation" in charts:
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["correlation"]),
                "title": "Matriz de Correlaciones",
                "explanation": (
                    "Relaciones estadísticas entre USD/CLP y sus principales drivers. "
                    "Correlación negativa USD/CLP-Cobre indica que alza del cobre fortalece el peso. "
                    "VIX-EEM negativa confirma que en risk-off los emergentes caen."
                ),
            })

        # Chart 5: Macro Dashboard
        if "macro_drivers" in charts:
            explanation = self._get_macro_dashboard_explanation(bundle)
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["macro_drivers"]),
                "title": "Dashboard Macroeconómico",
                "explanation": explanation,
            })

        # Chart 6: Risk Regime
        if "risk_regime" in charts:
            explanation = self._get_regime_explanation(bundle)
            blocks.append({
                "image": ChartGenerator.image_to_base64(charts["risk_regime"]),
                "title": "Régimen de Riesgo de Mercado",
                "explanation": explanation,
            })

        return blocks

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

        # Executive Summary (First)
        sections.append("## Resumen Ejecutivo")
        sections.append(self._build_executive_summary(bundle, forecast, horizon))

        # Forecast table
        sections.append("## Proyección Cuantitativa")
        sections.append(self._build_forecast_table(forecast))

        # NOTE: Chart explanations are now embedded with charts in template

        # Technical Analysis
        sections.append("## Análisis Técnico")
        sections.append(self._build_technical_analysis(bundle))

        # Risk Regime Assessment
        sections.append("## Régimen de Riesgo de Mercado")
        sections.append(self._build_risk_regime(bundle))

        # Fundamental Factors
        sections.append("## Factores Fundamentales")
        sections.append(self._build_fundamental_factors(bundle))

        # Trading Recommendations
        sections.append("## Recomendaciones Operativas")
        sections.append(self._build_trading_recommendations(bundle, forecast))

        # Methodology
        sections.append("## Metodología y Validación")
        sections.append(self._build_methodology(artifacts))

        # Risk Factors
        sections.append("## Factores de Riesgo")
        sections.append(self._build_risk_factors(bundle, forecast))

        # Conclusion
        sections.append("## Conclusión")
        sections.append(self._build_conclusion(bundle, forecast))

        # Sources
        sections.append("## Fuentes de Datos")
        sections.append(bundle.sources.as_markdown())

        # Disclaimer
        sections.append("## Disclaimer")
        sections.append(self._build_disclaimer())

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
        """Build methodology section with model justification."""

        # Justificacion del ensemble
        justification = """
### Justificacion de la Seleccion del Modelo

Se opto por un **modelo ensemble** que combina tres metodologias complementarias:

#### 1. ARIMA-GARCH (Peso: ~50%)
**Por que**: Captura patrones autorregresivos y volatilidad condicional heterocedástica,
ideal para series financieras con clusters de volatilidad como USD/CLP.

- **Fortalezas**: Modela bien la inercia del tipo de cambio y cambios de volatilidad
- **Uso**: Proyeccion de corto plazo (1-7 dias) con intervalos de confianza dinamicos

#### 2. VAR - Vector Autoregression (Peso: ~46%)
**Por que**: Modela relaciones multivariadas entre USD/CLP, cobre, DXY y TPM,
capturando interdependencias macroeconomicas.

- **Fortalezas**: Captura transmision de shocks entre variables (ej: caida del cobre → depreciacion CLP)
- **Uso**: Incorpora informacion fundamental para forecasts estructurales

#### 3. Random Forest (Peso: ~5%)
**Por que**: Modelo no lineal que captura relaciones complejas que ARIMA/VAR no ven.

- **Fortalezas**: Maneja no linealidades, umbrales, interacciones de alto orden
- **Limitacion**: Menor peso por ser "caja negra" con menor interpretabilidad
- **Uso**: Diversificador que reduce overfitting del ensemble

### Determinacion de Pesos

Los pesos se calculan dinamicamente mediante:
- **Inverse RMSE**: Modelos con menor error historico reciben mayor peso
- **Rolling Window**: Ventana de validacion de 90 dias para capturar regimen reciente
- **Recalibracion**: Pesos se actualizan en cada ejecucion segun performance reciente

### Intervalos de Confianza

Se generan mediante **simulacion Monte Carlo**:
1. Extraccion de residuales historicos del ensemble
2. 1,000 trayectorias simuladas con bootstrap de residuales
3. Percentiles 10/90 (IC 80%) y 2.5/97.5 (IC 95%)

Este enfoque captura mejor la incertidumbre que intervalos parametricos.
"""

        weights = artifacts.get("weights", {})
        if weights:
            weights_str = ", ".join(f"{k}: {v:.2f}" for k, v in weights.items())
            current_weights = f"\n**Pesos actuales del ensemble**: {weights_str}\n"
        else:
            current_weights = ""

        return justification + current_weights

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

    def _build_executive_summary(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
        horizon: str,
    ) -> str:
        """Build comprehensive executive summary."""
        if not forecast.series:
            return "Sin proyección disponible."

        spot = bundle.indicators.get("usdclp_spot")
        if not spot:
            return "Datos insuficientes para resumen ejecutivo."

        last_point = forecast.series[-1]
        move_pct = ((last_point.mean / spot.value) - 1) * 100
        range_pct = ((last_point.ci95_high - last_point.ci95_low) / last_point.mean) * 100

        if move_pct > 0.5:
            trend = "Alcista"
            bias = "depreciación del peso"
        elif move_pct < -0.5:
            trend = "Bajista"
            bias = "apreciación del peso"
        else:
            trend = "Lateral"
            bias = "estabilidad"

        # Volatility assessment
        from ..analysis.technical import compute_technicals
        technicals = compute_technicals(bundle.usdclp_series)
        current_vol = technicals["hist_vol_30"] * 100  # Convert to percentage

        if current_vol > 15:
            vol_desc = "elevada"
        elif current_vol > 10:
            vol_desc = "moderada"
        else:
            vol_desc = "baja"

        summary = (
            f"**Sesgo direccional:** {trend} ({move_pct:+.2f}% proyectado). "
            f"El modelo ensemble anticipa {bias} hacia {last_point.mean:.1f} CLP en {horizon}. "
            f"\n\n"
            f"**Nivel actual:** {spot.value:.1f} CLP/USD. "
            f"**Rango proyectado (95%):** {last_point.ci95_low:.1f} - {last_point.ci95_high:.1f} CLP. "
            f"**Incertidumbre:** ±{range_pct:.1f}% (volatilidad histórica 30d: {current_vol:.1f}%).\n\n"
            f"**Para importadores:** Considerar estrategia de cobertura escalonada. "
            f"Aprovechar retrocesos hacia {last_point.ci80_low:.1f} CLP para ejecutar forwards. "
            f"Mantener 40-60% de exposición cubierta dado contexto de volatilidad {vol_desc}."
        )

        return summary

    def _build_technical_analysis(self, bundle: DataBundle) -> str:
        """Build technical analysis section."""
        from ..analysis.technical import compute_technicals

        try:
            technicals = compute_technicals(bundle.usdclp_series)
        except Exception as e:
            return f"No se pudo completar análisis técnico: {e}"

        rsi = technicals["rsi_14"]
        macd = technicals["macd"]
        macd_signal = technicals["macd_signal"]
        ma_5 = technicals["ma_5"]
        ma_20 = technicals["ma_20"]
        ma_50 = technicals["ma_50"]
        bb_upper = technicals["bb_upper"]
        bb_lower = technicals["bb_lower"]
        latest_close = technicals["latest_close"]

        # RSI interpretation
        if rsi > 70:
            rsi_desc = "**Sobrecompra** (RSI > 70) - Posible corrección a la baja"
        elif rsi < 30:
            rsi_desc = "**Sobreventa** (RSI < 30) - Posible rebote alcista"
        elif rsi > 50:
            rsi_desc = "Momentum alcista moderado"
        else:
            rsi_desc = "Momentum bajista moderado"

        # MACD interpretation
        macd_diff = macd - macd_signal
        if macd_diff > 0:
            macd_desc = "**Señal alcista** (MACD > Signal) - Momentum positivo"
        else:
            macd_desc = "**Señal bajista** (MACD < Signal) - Momentum negativo"

        # Moving averages
        if latest_close > ma_50:
            ma_trend = "Tendencia alcista de medio plazo (precio > MA 50)"
        else:
            ma_trend = "Tendencia bajista de medio plazo (precio < MA 50)"

        # Bollinger Bands
        bb_position = (latest_close - bb_lower) / (bb_upper - bb_lower)
        if bb_position > 0.8:
            bb_desc = "Cercano a banda superior - Posible resistencia"
        elif bb_position < 0.2:
            bb_desc = "Cercano a banda inferior - Posible soporte"
        else:
            bb_desc = "Dentro de bandas normales"

        analysis = (
            f"**RSI (14 períodos):** {rsi:.1f} - {rsi_desc}\n\n"
            f"**MACD:** {macd:.2f} vs Signal {macd_signal:.2f} - {macd_desc}\n\n"
            f"**Medias Móviles:**\n"
            f"- MA 5: {ma_5:.1f} CLP\n"
            f"- MA 20: {ma_20:.1f} CLP\n"
            f"- MA 50: {ma_50:.1f} CLP\n"
            f"- {ma_trend}\n\n"
            f"**Bollinger Bands:** [{bb_lower:.1f}, {bb_upper:.1f}] - {bb_desc}\n\n"
            f"**Soporte/Resistencia:**\n"
            f"- Soporte técnico: {technicals['support']:.1f} CLP\n"
            f"- Resistencia técnica: {technicals['resistance']:.1f} CLP"
        )

        return analysis

    def _build_risk_regime(self, bundle: DataBundle) -> str:
        """Build risk regime assessment section."""
        from ..analysis.macro import compute_risk_gauge

        try:
            gauge = compute_risk_gauge(bundle)
        except (KeyError, AttributeError) as e:
            return (
                f"Análisis de régimen no disponible (datos insuficientes: DXY, VIX, EEM).\n\n"
                f"El régimen de riesgo global es un indicador clave para proyectar flujos "
                f"hacia activos emergentes como el peso chileno."
            )

        # Interpretation based on regime
        if gauge.regime == "Risk-on":
            interpretation = (
                "El mercado presenta **apetito por riesgo elevado**, favorable para "
                "activos emergentes. Este contexto típicamente fortalece al peso chileno "
                "por entrada de capitales hacia mercados de mayor rendimiento."
            )
            implications = (
                "- Presión apreciativa sobre CLP (bajista USD/CLP)\n"
                "- Mayor demanda por activos locales\n"
                "- Flujos de portafolio positivos"
            )
        elif gauge.regime == "Risk-off":
            interpretation = (
                "El mercado presenta **aversión al riesgo**, con flujos hacia activos "
                "refugio (USD, bonos del Tesoro). Este contexto típicamente debilita "
                "monedas emergentes como el peso chileno."
            )
            implications = (
                "- Presión depreciativa sobre CLP (alcista USD/CLP)\n"
                "- Salida de capitales desde emergentes\n"
                "- Volatilidad elevada en FX"
            )
        else:
            interpretation = (
                "El mercado presenta **señales mixtas**, sin sesgo claro hacia risk-on "
                "o risk-off. En este contexto, factores locales (cobre, TPM) tendrán "
                "mayor peso relativo."
            )
            implications = (
                "- CLP responde más a drivers domésticos\n"
                "- Volatilidad puede aumentar por incertidumbre\n"
                "- Monitorear cambios en indicadores globales"
            )

        regime_text = (
            f"**Régimen actual:** {gauge.regime}\n\n"
            f"{interpretation}\n\n"
            f"**Indicadores clave (cambio 5 días):**\n"
            f"- DXY (Dólar global): {gauge.dxy_change:+.2f}%\n"
            f"- VIX (Volatilidad): {gauge.vix_change:+.2f}%\n"
            f"- EEM (EM ETF): {gauge.eem_change:+.2f}%\n\n"
            f"**Implicancias para USD/CLP:**\n"
            f"{implications}"
        )

        return regime_text

    def _build_fundamental_factors(self, bundle: DataBundle) -> str:
        """Build fundamental factors table section."""
        from ..analysis.fundamental import extract_quant_factors, build_quant_factors

        try:
            factors = extract_quant_factors(bundle)
            factors_df = build_quant_factors(factors)

            # Convert dataframe to markdown table
            table_md = factors_df.to_markdown(index=False)

            intro = (
                "Factores cuantitativos fundamentales que influyen en la dinámica de USD/CLP. "
                "La tendencia reciente de cada factor indica su contribución al movimiento proyectado.\n\n"
            )

            return intro + table_md
        except Exception as e:
            return f"No se pudieron extraer factores fundamentales: {e}"

    def _build_trading_recommendations(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
    ) -> str:
        """Build trading recommendations section."""
        if not forecast.series:
            return "Sin recomendaciones disponibles."

        spot = bundle.indicators.get("usdclp_spot")
        if not spot:
            return "Datos insuficientes para recomendaciones."

        last_point = forecast.series[-1]
        mid_point = forecast.series[len(forecast.series) // 2] if len(forecast.series) > 1 else last_point

        # Calculate key levels
        entry_level = last_point.ci80_low
        target_level = last_point.mean
        stop_level = last_point.ci95_high

        recommendations = (
            f"**Para importadores (compradores de USD):**\n\n"
            f"1. **Nivel objetivo de cobertura:** {entry_level:.1f} - {mid_point.ci80_low:.1f} CLP/USD\n"
            f"   - Ejecutar coberturas escalonadas en retrocesos\n"
            f"   - Objetivo: cubrir 40-60% de exposición en próximos 30 días\n\n"
            f"2. **Estrategia sugerida:**\n"
            f"   - Forward 1M: {entry_level:.1f} CLP (30% del volumen)\n"
            f"   - Forward 2M: {mid_point.mean:.1f} CLP (20% del volumen)\n"
            f"   - Spot flexible: Mantener 50% sin cobertura para aprovechar mejoras\n\n"
            f"3. **Stop loss / Revisión:**\n"
            f"   - Si USD/CLP supera {stop_level:.1f} CLP, reevaluar exposición\n"
            f"   - Triggers de alerta: Cobre < 3.80 USD/lb, DXY > 107 pts\n\n"
            f"**Para exportadores (vendedores de USD):**\n\n"
            f"1. **Nivel objetivo de venta:** {last_point.ci80_high:.1f} - {stop_level:.1f} CLP/USD\n"
            f"   - Aprovechar alzas para asegurar márgenes\n"
            f"   - Considerar opciones (call spread) para capturar upside\n\n"
            f"2. **Gestión de riesgo:**\n"
            f"   - No dejar más de 30% de flujos sin cobertura\n"
            f"   - Usar collar options si presupuesto permite\n"
            f"   - Revisión semanal de posiciones"
        )

        return recommendations

    def _build_risk_factors(
        self,
        bundle: DataBundle,
        forecast: ForecastResult,
    ) -> str:
        """Build risk factors section."""
        # Upside risks (CLP strengthening, USD/CLP down)
        upside_risks = [
            "**Alza inesperada del cobre** (> 4.50 USD/lb): Impulsaría flujos hacia CLP",
            "**Recorte TPM menor a lo esperado**: Mantendría diferencial de tasas favorable",
            "**Debilitamiento del dólar global**: DXY en tendencia bajista por política Fed",
            "**Régimen risk-on sostenido**: Flujos de portafolio hacia mercados emergentes",
            "**Sorpresa positiva en PIB Chile**: Fortalecería atractivo de activos locales",
        ]

        # Downside risks (CLP weakening, USD/CLP up)
        downside_risks = [
            "**Caída abrupta del cobre** (< 3.80 USD/lb): Deterioro en términos de intercambio",
            "**Escalada de tensiones geopolíticas**: Aversión al riesgo global (flight to safety)",
            "**Fed mantiene tasas altas por más tiempo**: Reduce atractivo de carry en CLP",
            "**Inestabilidad política doméstica**: Aumenta prima de riesgo país",
            "**Crisis en mercados emergentes**: Contagio desde otros EM (Brasil, México)",
            "**Shock inflacionario en Chile**: Presionaría al BCCh a acelerar recortes",
        ]

        risk_text = (
            f"**Riesgos al alza para CLP (USD/CLP a la baja):**\n\n"
            + "\n".join(f"- {risk}" for risk in upside_risks)
            + "\n\n"
            + f"**Riesgos a la baja para CLP (USD/CLP al alza):**\n\n"
            + "\n".join(f"- {risk}" for risk in downside_risks)
            + "\n\n"
            + "**Recomendación:** Monitorear activamente triggers mencionados. "
            "Mantener flexibilidad en estrategia de cobertura para ajustar rápidamente "
            "ante cambios en el entorno macro."
        )

        return risk_text

    def _build_disclaimer(self) -> str:
        """Build disclaimer section."""
        disclaimer = (
            "Este informe se proporciona únicamente con fines informativos y educativos. "
            "Las proyecciones presentadas son estimaciones estadísticas basadas en modelos "
            "econométricos y no constituyen asesoramiento financiero, de inversión o comercial.\n\n"
            "**Limitaciones importantes:**\n\n"
            "- Los modelos de pronóstico tienen precisión limitada y están sujetos a error\n"
            "- Los mercados financieros son inherentemente impredecibles\n"
            "- Los resultados pasados no garantizan resultados futuros\n"
            "- Los intervalos de confianza representan probabilidades, no certezas\n"
            "- Eventos inesperados pueden invalidar las proyecciones\n\n"
            "**Advertencia de riesgo:**\n\n"
            "El comercio de divisas (FX) y los derivados financieros conllevan riesgos sustanciales, "
            "incluyendo la pérdida total del capital invertido. Consulte siempre con asesores "
            "financieros calificados antes de tomar decisiones de cobertura o inversión.\n\n"
            "Los usuarios de este informe asumen total responsabilidad por sus decisiones y "
            "acuerdan eximir de responsabilidad a los creadores del sistema de pronóstico."
        )

        return disclaimer

    def _get_technical_panel_explanation(self, bundle: DataBundle) -> str:
        """Get concise explanation for technical panel chart."""
        from ..analysis.technical import compute_technicals

        try:
            technicals = compute_technicals(bundle.usdclp_series)
            rsi = technicals["rsi_14"]
            macd = technicals["macd"]
            macd_signal = technicals["macd_signal"]

            # RSI interpretation
            if rsi > 70:
                rsi_interp = "sobrecompra (>70)"
            elif rsi < 30:
                rsi_interp = "sobreventa (<30)"
            else:
                rsi_interp = f"neutral ({rsi:.1f})"

            # MACD interpretation
            if macd > macd_signal:
                macd_interp = "momentum positivo"
            else:
                macd_interp = "momentum negativo"

            return (
                f"Tres paneles técnicos: precio con Bollinger Bands (bandas de volatilidad), "
                f"RSI en {rsi_interp}, y MACD con {macd_interp}. "
                f"Las Bollinger Bands señalan zonas de sobreextensión cuando el precio toca las bandas."
            )

        except Exception:
            return (
                "Panel técnico mostrando precio con Bollinger Bands, RSI (14 períodos) para "
                "identificar sobrecompra/sobreventa, y MACD para momentum direccional. "
                "Datos técnicos no disponibles en este momento."
            )


    def _get_macro_dashboard_explanation(self, bundle: DataBundle) -> str:
        """Get concise explanation for macro dashboard chart."""
        copper = bundle.indicators.get("copper")
        tpm = bundle.indicators.get("tpm")

        if copper and tpm:
            return (
                f"Cuatro drivers fundamentales: Cobre ({copper.value:.2f} USD/lb) con relación inversa al USD/CLP, "
                f"TPM ({tpm.value:.2f}%) que determina diferencial de tasas, DXY como proxy de fortaleza USD global, "
                f"e IPC que guía política monetaria del BCCh."
            )
        else:
            return (
                "Panel integrado con los cuatro factores macroeconómicos clave: precio del Cobre (principal "
                "exportación chilena), TPM (tasa de política monetaria), DXY (índice del dólar), e IPC (inflación). "
                "Datos actuales no disponibles."
            )

    def _get_regime_explanation(self, bundle: DataBundle) -> str:
        """Get concise explanation for risk regime chart."""
        from ..analysis.macro import compute_risk_gauge

        try:
            gauge = compute_risk_gauge(bundle)
            regime = gauge.regime

            if regime == "Risk-on":
                regime_desc = "Risk-On: apetito por riesgo favorable a emergentes, positivo para CLP"
            elif regime == "Risk-off":
                regime_desc = "Risk-Off: aversión al riesgo presiona CLP hacia depreciación"
            else:
                regime_desc = "Mixto: señales contradictorias, factores locales tienen mayor peso"

            return (
                f"Régimen actual: {regime_desc}. Calculado con DXY (dólar refugio), "
                f"VIX (volatilidad implícita), y EEM (ETF emergentes). "
                f"Cambios en 5 días: DXY {gauge.dxy_change:+.1f}%, VIX {gauge.vix_change:+.1f}%, EEM {gauge.eem_change:+.1f}%."
            )

        except Exception:
            return (
                "Indicador del apetito por riesgo global usando DXY, VIX y EEM. "
                "En Risk-On, flujos favorecen emergentes (CLP aprecia). En Risk-Off, "
                "capitales huyen a activos refugio (CLP deprecia). Datos no disponibles."
            )
