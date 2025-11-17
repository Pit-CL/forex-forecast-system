#!/usr/bin/env python3
"""Monitoreo por hora de cambios bruscos USD/CLP"""
import sys
from pathlib import Path
from datetime import datetime
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.config import get_settings
from loguru import logger
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ALERT_THRESHOLD_1H = 1.0
ALERT_THRESHOLD_DAY = 2.0
ALERT_THRESHOLD_VOLATILITY = 1.5

def get_data():
    ticker = yf.Ticker("CLP=X")
    hist_1h = ticker.history(period="1d", interval="1h")
    hist_5d = ticker.history(period="5d", interval="1h")
    return hist_1h, hist_5d

def detect_alerts(hist_1h, hist_5d):
    alerts = []
    if hist_1h.empty or len(hist_1h) < 2:
        return alerts
    
    curr = hist_1h["Close"].iloc[-1]
    prev = hist_1h["Close"].iloc[-2] if len(hist_1h) >= 2 else curr
    open_p = hist_1h["Close"].iloc[0]
    
    change_1h = ((curr - prev) / prev) * 100
    if abs(change_1h) >= ALERT_THRESHOLD_1H:
        alerts.append({
            "type": "CAMBIO_1H",
            "severity": "HIGH" if abs(change_1h) >= 1.5 else "MEDIUM",
            "message": f"Cambio de {change_1h:+.2f}% en la última hora"
        })
    
    change_day = ((curr - open_p) / open_p) * 100
    if abs(change_day) >= ALERT_THRESHOLD_DAY:
        alerts.append({
            "type": "CAMBIO_DIA",
            "severity": "CRITICAL" if abs(change_day) >= 3.0 else "HIGH",
            "message": f"Cambio de {change_day:+.2f}% desde apertura del día"
        })
    
    if not hist_5d.empty and len(hist_5d) >= 24:
        recent_vol = hist_1h["Close"].tail(4).std() if len(hist_1h) >= 4 else 0
        avg_vol = hist_5d["Close"].rolling(4).std().mean()
        if avg_vol > 0 and recent_vol / avg_vol >= ALERT_THRESHOLD_VOLATILITY:
            alerts.append({
                "type": "VOLATILIDAD_ALTA",
                "severity": "MEDIUM",
                "message": f"Volatilidad {recent_vol/avg_vol:.1f}x superior al promedio"
            })
    
    return alerts

def generate_html(alerts, hist_1h):
    curr = hist_1h["Close"].iloc[-1]
    max_p = hist_1h["Close"].max()
    min_p = hist_1h["Close"].min()
    open_p = hist_1h["Close"].iloc[0]
    change_day = ((curr - open_p) / open_p) * 100
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    max_sev = "CRITICAL" if any(a["severity"] == "CRITICAL" for a in alerts) else "HIGH" if any(a["severity"] == "HIGH" for a in alerts) else "MEDIUM"
    color = {"CRITICAL": "#dc3545", "HIGH": "#fd7e14", "MEDIUM": "#ffc107"}[max_sev]
    icon = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡"}[max_sev]
    
    alert_items = ""
    for alert in alerts:
        badge_color = {"CRITICAL": "#dc3545", "HIGH": "#fd7e14", "MEDIUM": "#ffc107"}[alert["severity"]]
        alert_items += f"""<li style="background:white;border:1px solid #dee2e6;padding:15px;margin-bottom:10px;border-radius:6px;display:flex;align-items:center">
<div style="font-size:24px;margin-right:15px">{icon}</div>
<div style="flex:1">
<strong style="display:block;margin-bottom:5px">{alert["message"]}</strong>
<small style="color:#6c757d"><span style="display:inline-block;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:600;background:{badge_color};color:white">{alert["severity"]}</span> {alert["type"].replace("_", " ")}</small>
</div>
</li>"""
    
    return f"""<!DOCTYPE html>
<html><head><meta charset=UTF-8><title>{icon} Alerta USD/CLP</title>
<style>body{{font-family:Arial,sans-serif;margin:0;padding:0;background:#f5f5f5}}.container{{max-width:650px;margin:20px auto;background:white;border-radius:12px;box-shadow:0 4px 6px rgba(0,0,0,0.1)}}.header{{background:linear-gradient(135deg,{color} 0%,{color}dd 100%);color:white;padding:30px;text-align:center}}.header h1{{margin:0;font-size:28px}}.content{{padding:30px}}.alert-box{{background:#fff3cd;border-left:4px solid {color};padding:20px;margin-bottom:20px;border-radius:4px}}.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:15px;margin:20px 0}}.metric{{background:#f8f9fa;padding:15px;border-radius:8px;text-align:center}}.metric-label{{font-size:12px;color:#6c757d;text-transform:uppercase;margin-bottom:5px}}.metric-value{{font-size:24px;font-weight:bold;color:#212529}}.metric-value.negative{{color:#dc3545}}.metric-value.positive{{color:#28a745}}.footer{{background:#f8f9fa;padding:20px;text-align:center;font-size:12px;color:#6c757d}}</style>
</head><body>
<div class=container>
<div class=header><h1>{icon} Alerta de Cambio Brusco USD/CLP</h1><div style="margin-top:10px;opacity:0.9">{timestamp} (Hora Chile)</div></div>
<div class=content>
<div class=alert-box><h3 style="margin-top:0;color:#856404">⚠️ Se detectaron {len(alerts)} alerta(s) de movimiento significativo</h3>
<p>El sistema de monitoreo en tiempo real ha detectado cambios importantes en el tipo de cambio USD/CLP.</p></div>
<div class=metrics>
<div class=metric><div class=metric-label>Precio Actual</div><div class=metric-value>${curr:.2f}</div></div>
<div class=metric><div class=metric-label>Cambio Hoy</div><div class="metric-value {"negative" if change_day < 0 else "positive"}">{change_day:+.2f}%</div></div>
<div class=metric><div class=metric-label>Máximo Hoy</div><div class=metric-value>${max_p:.2f}</div></div>
<div class=metric><div class=metric-label>Mínimo Hoy</div><div class=metric-value>${min_p:.2f}</div></div>
</div>
<h3>🔔 Alertas Detectadas</h3>
<ul style="list-style:none;padding:0">{alert_items}</ul>
<div style="background:#e7f3ff;padding:20px;border-radius:8px;margin-top:20px">
<h3 style="margin-top:0;color:#004085">📊 Resumen Intradía (últimas 24 horas)</h3>
<p><strong>Rango:</strong> ${min_p:.2f} - ${max_p:.2f} CLP</p>
<p><strong>Amplitud:</strong> {((max_p - min_p) / min_p * 100):.2f}% ({max_p - min_p:.2f} CLP)</p>
<p><strong>Tendencia:</strong> {"📉 Bajista" if change_day < 0 else "📈 Alcista"} ({change_day:+.2f}%)</p>
</div>
</div>
<div class=footer><p><strong>Sistema de Monitoreo USD/CLP en Tiempo Real</strong></p>
<p>Monitoreo cada hora • Datos de yfinance con delay ~5-15 min</p>
<p>🤖 Generado con Claude Code</p></div>
</div></body></html>"""

def send_email(html, alerts):
    settings = get_settings()
    max_sev = "CRITICAL" if any(a["severity"] == "CRITICAL" for a in alerts) else "HIGH" if any(a["severity"] == "HIGH" for a in alerts) else "MEDIUM"
    icons = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡"}
    subject = f"{icons[max_sev]} ALERTA USD/CLP - {max_sev} - {datetime.now().strftime("%H:%M")}"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_user
    msg["To"] = ", ".join(settings.email_recipients)
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.gmail_user, settings.gmail_app_password)
            server.send_message(msg)
        logger.info(f"✅ Alerta enviada: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando: {e}")
        return False

def main():
    logger.info("=== Iniciando monitoreo por hora ===")
    try:
        hist_1h, hist_5d = get_data()
        if hist_1h.empty:
            logger.warning("No hay datos")
            return
        
        logger.info(f"Datos: {len(hist_1h)} puntos (1h), {len(hist_5d)} puntos (5d)")
        alerts = detect_alerts(hist_1h, hist_5d)
        
        if not alerts:
            logger.info("✓ No se detectaron cambios significativos")
            return
        
        logger.warning(f"⚠️ {len(alerts)} alerta(s)")
        for a in alerts:
            logger.warning(f"  - {a['type']}: {a['message']}")
        
        html = generate_html(alerts, hist_1h)
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        email_path = output_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        email_path.write_text(html)
        logger.info(f"📧 Email guardado: {email_path}")
        
        send_email(html, alerts)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
