#!/usr/bin/env python3
"""
Script para generar correo HTML y PDF simple para cada horizonte de pronóstico.

Este script genera:
1. Un correo HTML con gráfico inline (base64) - será convertido a CID por send_unified_email.py
2. Un PDF simple (~30KB) con resumen ejecutivo

Uso:
    python scripts/test_email_and_pdf.py --horizon 7d
    python scripts/test_email_and_pdf.py --horizon 15d
    python scripts/test_email_and_pdf.py --horizon 30d
    python scripts/test_email_and_pdf.py --horizon 90d

Salida:
    - output/email_{horizon}.html (correo HTML con base64 images)
    - output/report_{horizon}.pdf (PDF simple ~30KB)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import io
import base64

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, AutoDateLocator

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    print("⚠️  WeasyPrint no disponible - PDF no será generado")


def create_forecast_chart(horizon: str) -> bytes:
    """Create a forecast chart for the given horizon and return as base64."""
    horizon_days = int(horizon.replace('d', ''))

    fig = Figure(figsize=(10, 6))
    ax = fig.add_subplot(111)

    # Generate sample USD/CLP data (historical)
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    prices = 926 + np.cumsum(np.random.randn(30) * 2)

    # Historical data
    ax.plot(dates, prices, 'o-', color='#004f71', linewidth=2, markersize=4, label='Histórico')

    # Forecast
    forecast_dates = pd.date_range(start=dates[-1] + timedelta(days=1), periods=horizon_days, freq='D')
    forecast_prices = prices[-1] + np.cumsum(np.random.randn(horizon_days) * 1.5)
    ax.plot(forecast_dates, forecast_prices, 's--', color='#ff6348', linewidth=2, markersize=5, label='Pronóstico')

    # Confidence bands (80%)
    ci_width = 10 + (horizon_days * 0.5)  # Wider bands for longer horizons
    upper_band = forecast_prices + ci_width
    lower_band = forecast_prices - ci_width
    ax.fill_between(forecast_dates, lower_band, upper_band, alpha=0.2, color='#ff6348', label='IC 80%')

    ax.set_xlabel('Fecha', fontsize=10)
    ax.set_ylabel('USD/CLP', fontsize=10)
    ax.set_title(f'Pronóstico USD/CLP {horizon} - Con Integración de Cobre', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Format date axis to prevent overlapping labels
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
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    plt.close(fig)
    return img_base64


def generate_email_html(horizon: str, chart_base64: str) -> str:
    """Generate HTML email content for the given horizon."""
    horizon_days = int(horizon.replace('d', ''))

    # Calculate sample forecast metrics
    current_price = 926.00
    forecast_price = 925.80
    change_pct = ((forecast_price - current_price) / current_price) * 100

    # Determine bias
    if change_pct > 0.3:
        bias = "ALCISTA"
        bias_emoji = "📈"
    elif change_pct < -0.3:
        bias = "BAJISTA"
        bias_emoji = "📉"
    else:
        bias = "NEUTRAL"
        bias_emoji = "➡️"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Pronóstico USD/CLP {horizon}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .email-container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #004f71 0%, #003a54 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .header .subtitle {{
            margin-top: 8px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .copper-badge {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #004f71;
        }}
        .metric-label {{
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        .chart-container {{
            margin: 25px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .recommendations {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .recommendations h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
            text-align: center;
            font-size: 11px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>{bias_emoji} Pronóstico USD/CLP {horizon}</h1>
            <div class="subtitle">Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} (Chile)</div>
            <span class="copper-badge">✨ CON INTEGRACIÓN DE COBRE</span>
        </div>

        <div class="metrics">
            <div class="metric-box">
                <div class="metric-label">Precio Actual</div>
                <div class="metric-value">${current_price:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Pronóstico {horizon}</div>
                <div class="metric-value">${forecast_price:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Cambio Esperado</div>
                <div class="metric-value">{change_pct:+.2f}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Sesgo</div>
                <div class="metric-value">{bias}</div>
            </div>
        </div>

        <div class="chart-container">
            <img src="data:image/png;base64,{chart_base64}" alt="Gráfico de Pronóstico">
        </div>

        <div class="recommendations">
            <h3>💡 Recomendaciones Principales</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Importadores:</strong> Coberturas escalonadas 20-30-30-20%</li>
                <li><strong>Exportadores:</strong> Estrategia neutral, vender en extremos de rango</li>
                <li><strong>Traders:</strong> Range-bound trading, vender volatilidad</li>
            </ul>
        </div>

        <div class="footer">
            <strong>Sistema Automático de Pronóstico USD/CLP</strong><br>
            Horizonte: {horizon_days} días | Modelo: Chronos-T5 con integración de Cobre<br>
            <em>Este informe no constituye asesoría financiera.</em>
        </div>
    </div>
</body>
</html>
"""
    return html


def generate_pdf_html(horizon: str) -> str:
    """Generate HTML content for PDF conversion."""
    horizon_days = int(horizon.replace('d', ''))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: Letter;
            margin: 2cm;
        }}
        body {{
            font-family: Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: #004f71;
            color: white;
            padding: 20px;
            text-align: center;
            margin: -2cm -2cm 20px -2cm;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .copper-badge {{
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 11px;
            display: inline-block;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 20px;
        }}
        .section h2 {{
            color: #004f71;
            border-bottom: 2px solid #004f71;
            padding-bottom: 8px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}
        .metric-box {{
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #004f71;
        }}
        .metric-label {{
            font-size: 11px;
            color: #6c757d;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #004f71;
            color: white;
            font-size: 12px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 2px solid #e9ecef;
            text-align: center;
            font-size: 10px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Informe de Pronóstico USD/CLP</h1>
        <div>Horizonte: {horizon_days} días | {datetime.now().strftime('%d/%m/%Y %H:%M')} (Chile)</div>
        <span class="copper-badge">✨ CON INTEGRACIÓN DE COBRE</span>
    </div>

    <div class="section">
        <h2>🎯 Resumen Ejecutivo</h2>
        <p>
            El sistema de pronóstico USD/CLP proyecta un movimiento <strong>NEUTRAL</strong> para los próximos {horizon_days} días.
            Esta proyección incorpora <strong>11 features técnicas del precio del cobre</strong> (HG=F - COMEX Copper Futures).
        </p>
    </div>

    <div class="section">
        <h2>📈 Métricas Clave</h2>
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-label">Precio Actual</div>
                <div class="metric-value">$926.00</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Pronóstico {horizon}</div>
                <div class="metric-value">$925.80</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Cambio</div>
                <div class="metric-value">-0.02%</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>💡 Recomendaciones por Perfil</h2>
        <table>
            <tr>
                <th>Perfil</th>
                <th>Recomendación</th>
            </tr>
            <tr>
                <td><strong>Importadores</strong></td>
                <td>Coberturas escalonadas 20-30-30-20% en retrocesos a zona $920-925</td>
            </tr>
            <tr>
                <td><strong>Exportadores</strong></td>
                <td>Estrategia neutral, vender USD en extremos superiores del rango proyectado</td>
            </tr>
            <tr>
                <td><strong>Traders</strong></td>
                <td>Range-bound trading, vender volatilidad implícita</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>🔬 Metodología</h2>
        <p>
            Pronóstico generado con modelo <strong>Chronos-T5 (Amazon)</strong> fine-tuned con:
        </p>
        <ul>
            <li>Datos históricos USD/CLP (5 años)</li>
            <li>Indicadores macroeconómicos (TPM, IPC, IMACEC)</li>
            <li>Indicadores internacionales (DXY, VIX, EEM, Fed Funds)</li>
            <li><strong>11 features técnicas del precio del cobre (HG=F) - NUEVO</strong></li>
        </ul>
    </div>

    <div class="footer">
        <strong>USD/CLP Forecasting System - Con Integración de Cobre</strong><br>
        Generado: {datetime.now().strftime('%d/%m/%Y %H:%M (Chile)')}<br>
        <em>Este informe no constituye asesoría financiera.</em>
    </div>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description='Generar email HTML y PDF simple para pronóstico')
    parser.add_argument('--horizon', type=str, required=True, choices=['7d', '15d', '30d', '90d'],
                        help='Horizonte de pronóstico (7d, 15d, 30d, 90d)')
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"Generando email y PDF para horizonte: {args.horizon}")
    print("=" * 60)

    # 1. Generate chart
    print("\n1. Generando gráfico de pronóstico...")
    chart_base64 = create_forecast_chart(args.horizon)
    print(f"   ✓ Gráfico generado ({len(chart_base64)} caracteres base64)")

    # 2. Generate email HTML
    print("\n2. Generando email HTML...")
    email_html = generate_email_html(args.horizon, chart_base64)
    email_path = output_dir / f"email_{args.horizon}.html"
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(email_html)
    print(f"   ✓ Email HTML guardado: {email_path}")

    # 3. Generate PDF
    print("\n3. Generando PDF simple...")
    if WEASYPRINT_AVAILABLE:
        pdf_html = generate_pdf_html(args.horizon)
        pdf_path = output_dir / f"report_{args.horizon}.pdf"
        HTML(string=pdf_html).write_pdf(pdf_path)
        print(f"   ✓ PDF guardado: {pdf_path}")
    else:
        print("   ⚠ WeasyPrint no disponible - PDF no generado")

    print("\n" + "=" * 60)
    print("✅ Generación completada exitosamente")
    print("\nArchivos generados:")
    print(f"  - Email: {email_path}")
    if WEASYPRINT_AVAILABLE:
        print(f"  - PDF:   {pdf_path}")
    print("\nEl email contiene imágenes base64 que serán convertidas a CID")
    print("por send_unified_email.py antes de enviar.")


if __name__ == "__main__":
    main()
