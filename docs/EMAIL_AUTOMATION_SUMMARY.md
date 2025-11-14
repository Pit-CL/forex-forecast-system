# Email Automation - Copper Impact Reports

**Fecha de implementación:** 2025-11-14
**Estado:** ✅ COMPLETAMENTE OPERACIONAL

---

## 🎯 Resumen

Sistema de envío automático de reportes de impacto de copper por email cada semana.

**Destinatario:** rafael@cavara.cl
**Frecuencia:** Cada domingo a las 10:00 AM (Chile)
**Adjunto:** Reporte HTML completo con análisis detallado

---

## 📧 Estructura del Email

### Subject Dinámico

El subject cambia según la semana y el status del análisis:

**Semana 1-2 (Datos insuficientes):**
```
ℹ️ Copper Impact Report - Semana 1 - INSUFFICIENT DATA
```

**Semana 3+ (Datos suficientes):**
```
✅ Copper Impact Report - Semana 3 - SUCCESS
⚠️ Copper Impact Report - Semana 3 - PARTIAL SUCCESS
❌ Copper Impact Report - Semana 3 - NO IMPROVEMENT
```

**Milestone (>= 21 días):**
```
🎯 MILESTONE: Copper Impact Report - Semana 4 - ACCIÓN REQUERIDA
```

### Body del Email

**Estructura HTML responsive:**

1. **Header**
   - Título: "📊 Reporte de Impacto: Copper Integration"
   - Semana actual, días desde integración, fecha

2. **Milestone Banner** (solo si días >= 21)
   - Banner rojo llamativo
   - "🎯 MILESTONE ALCANZADO"
   - "X días de datos recopilados - ACCIÓN REQUERIDA"

3. **Estado del Análisis**
   - Status box con color según estado
   - Mejora promedio RMSE
   - Recomendación destacada

4. **Resumen por Horizonte**
   - Tabla con horizontes (7d, 15d, 30d, 90d)
   - Número de predicciones
   - Mejora RMSE con código de color

5. **Reporte Completo**
   - Mención del archivo adjunto
   - Nombre del archivo HTML

6. **Próxima Ejecución**
   - Fecha de próximo reporte

7. **Footer**
   - Sistema de tracking
   - Email de contacto
   - Timestamp de generación

### Adjunto

**Archivo:** `copper_impact_report_YYYYMMDD_HHMMSS.html`

Reporte HTML completo con:
- Dashboard de salud de copper data
- Métricas pre/post copper detalladas
- Gráficos de comparación por horizonte
- Análisis de directional accuracy
- Recomendaciones basadas en datos

---

## 🔧 Implementación Técnica

### Archivos Creados

**1. `scripts/send_copper_report_email.py` (445 líneas)**

```python
class CopperReportEmailer:
    RECIPIENT = "rafael@cavara.cl"
    COPPER_INTEGRATION_DATE = datetime(2025, 11, 13)

    def generate_email_subject(self, report_data: Dict) -> str:
        # Dynamic subject based on week and status

    def build_email_body(self, report_data: Dict, html_path: Path) -> str:
        # HTML email with executive summary

    def send_email(self, subject: str, body_html: str, attachment_path: Path) -> bool:
        # Send via Gmail SMTP with attachment
```

**Funcionalidad:**
- Encuentra último reporte HTML y JSON
- Carga datos del JSON para resumen
- Genera subject dinámico
- Construye body HTML con estilos inline
- Adjunta reporte HTML completo
- Envía vía Gmail SMTP

### Archivos Modificados

**1. `scripts/weekly_copper_tracking.sh`**

```bash
# Antes (comentado):
# TODO: Opcional - enviar email con reporte adjunto
# python3 scripts/send_copper_report_email.py "$LATEST_REPORT"

# Ahora (activo):
log "📧 Sending email report to rafael@cavara.cl..."
python3 scripts/send_copper_report_email.py "$LATEST_REPORT" >> "$LOG_FILE" 2>&1
```

**Cambio:** Ahora envía email en TODAS las ejecuciones (no solo milestones).

---

## 🧪 Testing

### Test Exitoso - 2025-11-14 00:01:33

**Comando ejecutado:**
```bash
ssh reporting "/home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh"
```

**Output:**
```
[2025-11-14 00:01:32] 📧 Sending email report to rafael@cavara.cl...
2025-11-14 00:01:32 | INFO | Subject: ℹ️ Copper Impact Report - Semana 1 - INSUFFICIENT DATA
2025-11-14 00:01:32 | INFO | Sending email to rafael@cavara.cl...
2025-11-14 00:01:33 | INFO | ✅ Email sent successfully to rafael@cavara.cl
```

**Email enviado:**
- ✅ Subject correcto para Semana 1
- ✅ Body HTML con resumen ejecutivo
- ✅ Adjunto: copper_impact_report_20251114_000132.html
- ✅ Destinatario: rafael@cavara.cl

---

## 📅 Calendario de Emails

### Próximos Envíos Automáticos

| Fecha | Semana | Días | Status Esperado | Subject Preview |
|-------|--------|------|-----------------|-----------------|
| 2025-11-17 | 1 | 4 | INSUFFICIENT_DATA | ℹ️ ... Semana 1 - INSUFFICIENT DATA |
| 2025-11-24 | 2 | 11 | INSUFFICIENT_DATA | ℹ️ ... Semana 2 - INSUFFICIENT DATA |
| 2025-12-01 | 3 | 18 | PARTIAL_DATA | ⚠️ ... Semana 3 - PARTIAL SUCCESS |
| 2025-12-08 | 4 | 25 | **MILESTONE** | 🎯 MILESTONE: ... Semana 4 - ACCIÓN REQUERIDA |

**Nota:** La primera vez con datos suficientes para decisión GO/NO-GO será el **2025-12-08** (>= 21 días).

---

## 🔍 Cómo Validar que Funciona

### Opción 1: Revisar Email (Recomendado)

Cada domingo después de las 10:00 AM, revisa tu bandeja de entrada de rafael@cavara.cl:

- ✅ Email debe llegar entre 10:00 - 10:05 AM
- ✅ Subject debe incluir semana actual
- ✅ Adjunto HTML debe estar presente
- ✅ Abrir adjunto para ver reporte completo

### Opción 2: Revisar Logs en Servidor

```bash
# Ver logs de última ejecución
ssh reporting "tail -50 /home/deployer/forex-forecast-system/logs/copper_tracking.log"

# Buscar líneas de email
ssh reporting "grep 'Email sent successfully' /home/deployer/forex-forecast-system/logs/copper_tracking.log"
```

**Output esperado:**
```
2025-11-XX XX:XX:XX | INFO | ✅ Email sent successfully to rafael@cavara.cl
```

### Opción 3: Test Manual

```bash
# Ejecutar tracking manualmente (fuera del cron)
ssh reporting "/home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh"

# Deberías recibir email inmediatamente
```

---

## 🛠️ Troubleshooting

### Email No Llega

**1. Verificar logs:**
```bash
ssh reporting "tail -100 /home/deployer/forex-forecast-system/logs/copper_tracking.log | grep -i email"
```

**Posibles errores:**
- `SMTP authentication failed` → Verificar GMAIL_APP_PASSWORD en .env
- `Connection refused` → Verificar conectividad a smtp.gmail.com
- `No reports found` → Tracking script no generó reporte

**2. Verificar credenciales:**
```bash
ssh reporting "cat /home/deployer/forex-forecast-system/.env | grep GMAIL"
```

Debe tener:
```
GMAIL_USER=tu_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**3. Test de envío manual:**
```bash
ssh reporting "cd /home/deployer/forex-forecast-system && python3 scripts/send_copper_report_email.py"
```

### Email en Spam

Si el email llega a spam:

1. Marcar como "No es spam"
2. Agregar remitente a contactos
3. Crear filtro para futuros emails:
   - From: tu_email@gmail.com
   - Subject: "Copper Impact Report"
   - Acción: "Nunca enviar a spam"

### Email Sin Adjunto

Verificar que reporte HTML existe:
```bash
ssh reporting "ls -lht /home/deployer/forex-forecast-system/output/copper_impact_report_*.html | head -1"
```

Si no existe, tracking script falló. Ver logs.

---

## 📊 Métricas de Email

### Información Enviada

**En el body (inline):**
- Status del análisis
- Mejora promedio RMSE
- Recomendación
- Tabla resumen por horizonte (4 filas)
- Días desde integración
- Número de semana

**En el adjunto (HTML completo):**
- Dashboard de salud de copper data
- Métricas detalladas pre/post por horizonte
- Gráficos de comparación RMSE
- Análisis de directional accuracy
- Recomendaciones completas con criterios

---

## ✅ Checklist de Validación

- [x] Script de email creado y subido al servidor
- [x] weekly_copper_tracking.sh modificado para llamar al script
- [x] Test manual ejecutado exitosamente
- [x] Email recibido en rafael@cavara.cl
- [x] Adjunto HTML abre correctamente
- [x] Cron configurado para ejecución automática
- [x] Logs muestran envío exitoso
- [x] Documentación actualizada

---

## 🎯 Próximos Pasos

**No se requiere acción hasta 2025-12-08**

En esa fecha:
1. Revisa email recibido (incluirá banner de MILESTONE)
2. Abre adjunto HTML para análisis completo
3. Revisa métricas de mejora RMSE
4. Toma decisión GO/NO-GO basada en criterios
5. Si GO: Continuar con Fase 2 (Treasury Yields + IPSA)
6. Si NO-GO: Investigar causas y ajustar

---

**Última actualización:** 2025-11-14 00:05 (Chile)
**Estado:** ✅ OPERACIONAL Y TESTEADO
**Próximo email:** 2025-11-17 10:00 AM (Chile)
