import requests
import json
from datetime import datetime
from typing import Optional

def send_slack_alert(webhook_url: str, message: str, severity: str = "warning") -> bool:
    """Send alert to Slack via webhook"""
    if not webhook_url:
        return False
    
    # Color based on severity
    color_map = {
        "info": "#36a64f",      # Green
        "warning": "#ff9800",   # Orange
        "critical": "#f44336"   # Red
    }
    
    payload = {
        "attachments": [{
            "color": color_map.get(severity, "#ff9800"),
            "title": "🚨 Forex Forecast Alert",
            "text": message,
            "footer": "Forex Forecast System",
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Slack alert: {e}")
        return False

def send_forecast_divergence_alert(
    webhook_url: str,
    horizon: str,
    change_pct: float,
    forecast_price: float,
    current_price: float,
    threshold: float = 5.0
) -> bool:
    """Send forecast divergence alert to Slack"""
    
    direction = "📈 ALZA" if change_pct > 0 else "📉 BAJA"
    severity = "critical" if abs(change_pct) > 10 else "warning"
    
    message = f"""
*Pronóstico {horizon.upper()} muestra cambio significativo*

{direction} *{change_pct:+.2f}%* (threshold: {threshold}%)

• Precio actual: ${current_price:,.2f}
• Pronóstico {horizon}: ${forecast_price:,.2f}
• Cambio: ${forecast_price - current_price:+,.2f}

⚠️ Revisar dashboard para más detalles
"""
    
    return send_slack_alert(webhook_url, message, severity)


def send_fallback_activation_alert(
    webhook_url: str,
    horizon: str,
    reason: str,
    last_generation: str,
    hours_since_update: float
) -> bool:
    """Send alert when forecast falls back to mock/fallback data"""
    
    severity = "critical" if hours_since_update > 72 else "warning"
    
    message = f"""
*Forecast Fallback Activated - {horizon.upper()}*

*Razon:* {reason}
*Ultima generacion:* {last_generation}
*Tiempo transcurrido:* {hours_since_update:.1f} horas

*Accion Recomendada:*
1. Verificar ejecucion de cron job
2. Revisar logs: /opt/forex-forecast-system/logs/auto_update_*.log
3. Ejecutar manualmente: python3 scripts/generate_real_forecasts.py --all

Dashboard mostrando datos de fallback temporalmente.
"""
    
    return send_slack_alert(webhook_url, message, severity)
