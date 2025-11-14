#!/bin/bash
#
# Weekly Copper Impact Tracking - Automated Execution
#
# Este script se ejecuta automáticamente cada semana para medir
# el impacto de la integración de cobre en los forecasts.
#
# Configuración: Ejecutar vía cron cada domingo a las 10:00 AM
# Cron: 0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh
#
# Fecha de inicio: 2025-11-13 (deployment de copper)
# Período de tracking: 3 semanas (hasta 2025-12-04)
# Después de 3 semanas: Continúa ejecutando pero solo reporta si hay datos significativos

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/copper_tracking.log"
REPORT_DIR="$PROJECT_DIR/output"
COPPER_INTEGRATION_DATE="2025-11-13"

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "======================================================================="
log "WEEKLY COPPER TRACKING - Starting"
log "======================================================================="

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR"

# Calcular días desde integración
CURRENT_DATE=$(date +%Y-%m-%d)
DAYS_SINCE=$(( ( $(date -d "$CURRENT_DATE" +%s) - $(date -d "$COPPER_INTEGRATION_DATE" +%s) ) / 86400 ))

log "Days since copper integration: $DAYS_SINCE"

# Ejecutar script de tracking
log "Executing copper impact tracking script..."

if python3 scripts/track_copper_impact.py >> "$LOG_FILE" 2>&1; then
    log "✅ Tracking script executed successfully"

    # Encontrar el reporte HTML más reciente
    LATEST_REPORT=$(ls -t "$REPORT_DIR"/copper_impact_report_*.html 2>/dev/null | head -1)

    if [ -n "$LATEST_REPORT" ]; then
        log "📊 Report generated: $LATEST_REPORT"

        # Si han pasado >= 21 días (3 semanas), enviar notificación importante
        if [ $DAYS_SINCE -ge 21 ]; then
            log "🎯 MILESTONE REACHED: 3 weeks of data collected"
            log "📌 ACTION REQUIRED: Review copper impact report and make GO/NO-GO decision"

            # Enviar email con reporte adjunto
            log "📧 Sending email report to rafael@cavara.cl..."
            python3 scripts/send_copper_report_email.py "$LATEST_REPORT" >> "$LOG_FILE" 2>&1
        elif [ $DAYS_SINCE -ge 7 ]; then
            log "📊 Week $((DAYS_SINCE / 7)) report generated. Continue monitoring."

            # Enviar email con reporte adjunto
            log "📧 Sending email report to rafael@cavara.cl..."
            python3 scripts/send_copper_report_email.py "$LATEST_REPORT" >> "$LOG_FILE" 2>&1
        else
            log "ℹ️  Insufficient data for analysis. Report generated but awaiting more data."

            # Enviar email con reporte adjunto (incluso con datos insuficientes)
            log "📧 Sending email report to rafael@cavara.cl..."
            python3 scripts/send_copper_report_email.py "$LATEST_REPORT" >> "$LOG_FILE" 2>&1
        fi
    else
        log "⚠️  No HTML report found in $REPORT_DIR"
    fi
else
    log "❌ Tracking script failed. Check logs above for details."
    exit 1
fi

log "======================================================================="
log "WEEKLY COPPER TRACKING - Completed"
log "======================================================================="

# Cleanup: Mantener solo últimos 10 reportes
log "Cleaning up old reports (keeping last 10)..."
ls -t "$REPORT_DIR"/copper_impact_report_*.html 2>/dev/null | tail -n +11 | xargs -r rm
ls -t "$REPORT_DIR"/copper_impact_report_*.json 2>/dev/null | tail -n +11 | xargs -r rm

log "Next execution: $(date -d 'next sunday 10:00' +'%Y-%m-%d %H:%M')"

exit 0
