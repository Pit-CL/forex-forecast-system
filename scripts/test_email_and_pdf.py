"""
Script de prueba para generar correo electrónico y PDF de ejemplo.

Este script genera:
1. Un correo HTML completo (sin enviar) con datos de prueba
2. Un PDF de informe de ejemplo con gráficos y análisis

Uso:
    python scripts/test_email_and_pdf.py

Salida:
    - output/test_email_preview.html (correo HTML)
    - output/test_report_7d.pdf (PDF de informe)
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
import io
import base64

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from forex_core.notifications.email_builder import EmailContentBuilder
from forex_core.notifications.unified_email import ForecastData, SystemHealthData
from forex_core.config import get_settings


def create_sample_chart() -> bytes:
    """Create a sample forecast chart and return as base64."""
    fig = Figure(figsize=(10, 6))
    ax = fig.add_subplot(111)

    # Generate sample USD/CLP data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    prices = 950 + np.cumsum(np.random.randn(30) * 2)

    # Historical data
    ax.plot(dates, prices, 'o-', color='#004f71', linewidth=2, label='Histórico')

    # Forecast (7 days ahead)
    forecast_dates = pd.date_range(start=dates[-1] + timedelta(days=1), periods=7, freq='D')
    forecast_prices = prices[-1] + np.cumsum(np.random.randn(7) * 1.5)
    ax.plot(forecast_dates, forecast_prices, 's--', color='#ff6348', linewidth=2, label='Pronóstico')

    # Confidence bands
    upper_band = forecast_prices + 10
    lower_band = forecast_prices - 10
    ax.fill_between(forecast_dates, lower_band, upper_band, alpha=0.2, color='#ff6348')

    ax.set_xlabel('Fecha')
    ax.set_ylabel('USD/CLP')
    ax.set_title('Pronóstico USD/CLP 7 días - Con Copper Integration')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Format date axis to prevent overlapping labels
    from matplotlib.dates import DateFormatter, AutoDateLocator
    formatter = DateFormatter('%Y-%m-%d')
    locator = AutoDateLocator(maxticks=10)
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_major_locator(locator)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)

    # Save to bytes
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)

    # Convert to base64
    img_base64 = base64.b64encode(buf.read())

    plt.close(fig)
    return img_base64


def create_sample_pdf(output_path: Path) -> None:
    """Create a sample PDF report."""
    try:
        from weasyprint import HTML, CSS
        use_weasyprint = True
    except (ImportError, OSError) as e:
        print(f"⚠️  WeasyPrint no disponible (OK en local, funciona en servidor): {e}")
        print("   → Generando HTML alternativo en su lugar")
        use_weasyprint = False

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: Letter;
                margin: 2cm;
                @bottom-right {
                    content: "Página " counter(page) " de " counter(pages);
                    font-size: 10px;
                    color: #666;
                }
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                color: #333;
                line-height: 1.6;
            }
            .header {
                background: linear-gradient(135deg, #004f71 0%, #003a54 100%);
                color: white;
                padding: 30px;
                margin: -2cm -2cm 30px -2cm;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
            }
            .header .subtitle {
                margin-top: 10px;
                font-size: 16px;
                opacity: 0.9;
            }
            .section {
                margin-bottom: 30px;
                page-break-inside: avoid;
            }
            .section h2 {
                color: #004f71;
                border-bottom: 2px solid #004f71;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .metric-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 20px 0;
            }
            .metric-box {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #004f71;
            }
            .metric-label {
                font-size: 12px;
                color: #6c757d;
                margin-bottom: 5px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            .metric-value.positive {
                color: #28a745;
            }
            .metric-value.negative {
                color: #dc3545;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            th {
                background-color: #004f71;
                color: white;
                font-weight: 600;
            }
            .highlight {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }
            .footer {
                margin-top: 50px;
                padding-top: 20px;
                border-top: 2px solid #e9ecef;
                text-align: center;
                font-size: 11px;
                color: #6c757d;
            }
            .copper-badge {
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Informe de Pronóstico USD/CLP</h1>
            <div class="subtitle">Horizonte: 7 días | Generado: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """ (Chile)</div>
            <div style="margin-top: 10px;">
                <span class="copper-badge">✨ CON INTEGRACIÓN DE COBRE</span>
            </div>
        </div>

        <div class="section">
            <h2>🎯 Resumen Ejecutivo</h2>
            <p>
                El sistema de pronóstico USD/CLP proyecta un movimiento <strong>ALCISTA</strong> para los próximos 7 días,
                con una expectativa de cambio de <strong>+1.2%</strong> desde el nivel actual.
            </p>
            <p>
                <strong>Nuevo:</strong> Esta proyección incorpora <strong>11 features técnicas del precio del cobre</strong>
                (HG=F - COMEX Copper Futures), mejorando significativamente la capacidad predictiva del modelo.
            </p>
        </div>

        <div class="section">
            <h2>📈 Métricas Clave del Pronóstico</h2>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-label">Precio Actual</div>
                    <div class="metric-value">$954.20</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Pronóstico 7d</div>
                    <div class="metric-value positive">$965.65</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Cambio Esperado</div>
                    <div class="metric-value positive">+1.20%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Sesgo</div>
                    <div class="metric-value positive">ALCISTA</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Volatilidad</div>
                    <div class="metric-value">MEDIA</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Confianza 95%</div>
                    <div class="metric-value">945 - 986</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🔥 Integración de Cobre - Nuevas Features</h2>
            <p>
                El sistema ahora incorpora datos en tiempo real del precio del cobre (HG=F - COMEX),
                considerando que Chile exporta 50% en cobre. Las siguientes features fueron agregadas:
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Valor Actual</th>
                        <th>Impacto</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Retorno Cobre 1d</td>
                        <td>+0.8%</td>
                        <td>Positivo para CLP</td>
                    </tr>
                    <tr>
                        <td>Volatilidad Cobre 20d</td>
                        <td>23.4% (anualizada)</td>
                        <td>Moderada</td>
                    </tr>
                    <tr>
                        <td>RSI Cobre 14</td>
                        <td>58.3</td>
                        <td>Neutral</td>
                    </tr>
                    <tr>
                        <td>Tendencia Cobre</td>
                        <td>+1 (Alcista)</td>
                        <td>SMA20 > SMA50</td>
                    </tr>
                    <tr>
                        <td>Correlación Cobre-USD/CLP 90d</td>
                        <td>-0.687</td>
                        <td>Correlación negativa esperada</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📊 Principales Drivers del Pronóstico</h2>
            <ol style="font-size: 14px; line-height: 1.8;">
                <li><strong>Precio del Cobre (NUEVO):</strong> Tendencia alcista del cobre (+2.3% últimos 5 días) presiona a la baja el USD/CLP.</li>
                <li><strong>TPM Banco Central:</strong> Mantención de tasa en 5.50% mantiene diferencial con Fed estable.</li>
                <li><strong>DXY (Índice Dólar):</strong> Fortaleza moderada del dólar (DXY=104.2) limita descensos del USD/CLP.</li>
                <li><strong>Volatilidad VIX:</strong> VIX en 15.2 señala baja volatilidad global, favorable para emergentes.</li>
                <li><strong>Correlación Copper-USD/CLP:</strong> Correlación negativa histórica de -0.69 se mantiene, confirmando relación esperada.</li>
            </ol>
        </div>

        <div class="section">
            <h2>⚠️ Riesgos y Consideraciones</h2>
            <div class="highlight">
                <h3 style="margin-top: 0;">Riesgos Alcistas (USD/CLP sube):</h3>
                <ul>
                    <li>Corrección en precio del cobre (actualmente en zona alta)</li>
                    <li>Fortalecimiento inesperado del DXY por datos macro USA</li>
                    <li>Aumento sorpresivo de volatilidad global (VIX > 20)</li>
                </ul>

                <h3>Riesgos Bajistas (USD/CLP baja):</h3>
                <ul>
                    <li>Rally sostenido del cobre por demanda China</li>
                    <li>Intervención del Banco Central en mercado cambiario</li>
                    <li>Mejora sustancial en términos de intercambio Chile</li>
                </ul>
            </div>
        </div>

        <div class="section">
            <h2>💡 Recomendaciones por Perfil</h2>
            <table>
                <thead>
                    <tr>
                        <th>Perfil</th>
                        <th>Recomendación</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Importadores</strong></td>
                        <td>Cubrir 30-50% exposición en retrocesos hacia $950-952. Evitar compras masivas arriba de $960.</td>
                    </tr>
                    <tr>
                        <td><strong>Exportadores</strong></td>
                        <td>Esperar niveles superiores ($970+) para vender USD. Aprovechar rally del cobre para mejores tipos de cambio.</td>
                    </tr>
                    <tr>
                        <td><strong>Traders</strong></td>
                        <td>Long USD/CLP en pullbacks a $950-952, target IC80 superior ($972). Stop loss bajo $945.</td>
                    </tr>
                    <tr>
                        <td><strong>Tesorería Corporativa</strong></td>
                        <td>Estrategia escalonada: cubrir 20% actual, 30% en $952, 30% en $955, 20% en $958.</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🏥 Salud del Sistema</h2>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-label">Estado General</div>
                    <div class="metric-value">OPTIMAL</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Puntaje</div>
                    <div class="metric-value">95/100</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Últimas Predicciones</div>
                    <div class="metric-value">28</div>
                </div>
            </div>
            <p>
                <strong>Performance 7d:</strong> EXCELLENT (RMSE: 8.2 CLP, MAPE: 0.9%)<br>
                <strong>Copper Data Source:</strong> Yahoo Finance (HG=F) - ✅ Activo<br>
                <strong>Última Actualización Cobre:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """<br>
                <strong>Fuentes Totales:</strong> 15 (incluye 1 nueva: Copper Futures)
            </p>
        </div>

        <div class="section">
            <h2>🔬 Metodología</h2>
            <p>
                Este pronóstico fue generado usando el modelo <strong>Chronos-T5 (Amazon)</strong> con arquitectura
                de transformer pre-entrenado en series temporales. El modelo fue fine-tuned con:
            </p>
            <ul>
                <li>Datos históricos USD/CLP (5 años)</li>
                <li>Indicadores macroeconómicos Chile (TPM, Inflación, IMACEC)</li>
                <li>Indicadores internacionales (DXY, VIX, EEM, Fed Funds)</li>
                <li><strong>NUEVO: 11 features técnicas del precio del cobre (HG=F)</strong></li>
                <li>Eventos económicos y noticias relevantes</li>
            </ul>
            <p>
                <strong>Mejora esperada con Copper:</strong> +15-25% en accuracy (RMSE reduction)<br>
                <strong>Período de evaluación:</strong> 2-3 semanas post-deployment
            </p>
        </div>

        <div class="section">
            <h2>📚 Fuentes de Datos</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fuente</th>
                        <th>Indicador</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Yahoo Finance (NUEVO)</strong></td>
                        <td>Copper Futures (HG=F)</td>
                        <td style="color: #28a745;">✓ Activo</td>
                    </tr>
                    <tr>
                        <td>Banco Central de Chile</td>
                        <td>USD/CLP Observado, TPM</td>
                        <td style="color: #28a745;">✓ Activo</td>
                    </tr>
                    <tr>
                        <td>Mindicador API</td>
                        <td>IPC, IMACEC, Desempleo</td>
                        <td style="color: #28a745;">✓ Activo</td>
                    </tr>
                    <tr>
                        <td>FRED API</td>
                        <td>DXY, VIX, Fed Funds, EEM</td>
                        <td style="color: #28a745;">✓ Activo</td>
                    </tr>
                    <tr>
                        <td>Cleveland Fed</td>
                        <td>Dot Plot Projections</td>
                        <td style="color: #28a745;">✓ Activo</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>
                <strong>USD/CLP Forecasting System - MLOps Phase 2 ✨ with Copper Integration</strong><br>
                Generado automáticamente el """ + datetime.now().strftime('%d/%m/%Y a las %H:%M (Chile)') + """<br>
                <em>Este informe utiliza modelos de inteligencia artificial y no constituye asesoría financiera.</em><br>
                <em>Consulte con su asesor antes de tomar decisiones de inversión.</em><br><br>
                <strong>Versión:</strong> 2.1.0 | <strong>Modelo:</strong> Chronos-T5 | <strong>Copper Integration:</strong> ✅ Activo
            </p>
        </div>
    </body>
    </html>
    """

    # Convert HTML to PDF
    HTML(string=html_content).write_pdf(output_path)
    print(f"✅ PDF generado exitosamente: {output_path}")


def main():
    """Main function to generate test email and PDF."""
    print("=" * 70)
    print("GENERACIÓN DE CORREO Y PDF DE PRUEBA")
    print("=" * 70)
    print()

    # Get settings
    settings = get_settings()
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 1. Generate test email HTML
    print("1. Generando correo HTML de prueba...")
    print("-" * 70)

    # Create sample forecast data
    forecasts = [
        ForecastData(
            horizon="7d",
            current_price=954.20,
            forecast_price=965.65,
            change_pct=1.20,
            ci95_low=945.0,
            ci95_high=986.0,
            ci80_low=952.0,
            ci80_high=979.0,
            bias="ALCISTA",
            volatility="MEDIA",
            chart_preview=create_sample_chart(),
            top_drivers=[
                "Precio del cobre en tendencia alcista (+2.3% últimos 5d) - NUEVO",
                "TPM mantiene en 5.50%, diferencial con Fed estable",
                "DXY en 104.2, fortaleza moderada limita descensos",
                "VIX en 15.2 señala baja volatilidad global",
                "Correlación Copper-USD/CLP de -0.69 confirma relación esperada"
            ],
            timestamp=datetime.now()
        ),
        ForecastData(
            horizon="15d",
            current_price=954.20,
            forecast_price=971.50,
            change_pct=1.81,
            ci95_low=942.0,
            ci95_high=1001.0,
            ci80_low=955.0,
            ci80_high=988.0,
            bias="ALCISTA",
            volatility="MEDIA",
            top_drivers=[
                "Momentum positivo del cobre refuerza sesgo alcista CLP",
                "Términos de intercambio favorables para Chile",
                "Fed mantiene tasas, diferencial estable"
            ],
            timestamp=datetime.now()
        )
    ]

    # Create sample system health
    system_health = SystemHealthData(
        readiness_level="OPTIMAL",
        readiness_score=95.0,
        performance_status={
            "7d": "EXCELLENT",
            "15d": "EXCELLENT",
            "30d": "GOOD",
            "90d": "GOOD"
        },
        degradation_detected=False,
        degradation_details=[],
        recent_predictions=28,
        drift_detected=False,
        drift_details=[]
    )

    # Build email content
    builder = EmailContentBuilder()
    html_content = builder.build(
        forecasts=forecasts,
        system_health=system_health,
        priority="ROUTINE",
        pdf_attachments=[],
        current_date=datetime.now()
    )

    # Save email HTML
    email_path = output_dir / "test_email_preview.html"
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Correo HTML generado: {email_path}")
    print(f"   Tamaño: {len(html_content)} caracteres")
    print(f"   Pronósticos incluidos: {len(forecasts)}")
    print(f"   Prioridad: ROUTINE")
    print()

    # 2. Generate test PDF
    print("2. Generando PDF de informe de prueba...")
    print("-" * 70)

    pdf_path = output_dir / "test_report_7d.pdf"
    create_sample_pdf(pdf_path)
    print()

    # Summary
    print("=" * 70)
    print("✨ GENERACIÓN COMPLETADA")
    print("=" * 70)
    print()
    print("Archivos generados:")
    print(f"  1. Correo HTML: {email_path}")
    print(f"     → Abre este archivo en tu navegador para ver el correo")
    print()
    print(f"  2. PDF Informe:  {pdf_path}")
    print(f"     → Este sería el PDF adjunto en emails importantes")
    print()
    print("Características destacadas:")
    print("  ✅ Correo con diseño responsive (mobile-first)")
    print("  ✅ Secciones ejecutivas colapsadas para lectura rápida")
    print("  ✅ Gráficos inline con interpretaciones")
    print("  ✅ Sistema de prioridades (URGENT/ATTENTION/ROUTINE)")
    print("  ✅ Dashboard de salud del sistema")
    print("  ✅ Integración de copper claramente destacada")
    print()
    print("Nota: El correo NO fue enviado (solo preview HTML)")
    print("=" * 70)


if __name__ == "__main__":
    main()
