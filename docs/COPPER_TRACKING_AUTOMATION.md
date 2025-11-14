# Copper Impact Tracking - Sistema Automatizado

**Fecha de configuración:** 2025-11-13
**Estado:** ✅ COMPLETAMENTE AUTOMATIZADO

---

## 🎯 Resumen

El sistema de tracking de impacto de copper se ejecuta **automáticamente cada semana** sin intervención manual.

### ¿Qué hace?

- Analiza el impacto de la integración de cobre en los forecasts
- Compara métricas RMSE pre/post copper
- Genera reportes HTML visuales automáticamente
- Detecta cuándo hay datos suficientes para análisis
- Limpia reportes antiguos automáticamente

### ¿Cuándo ejecuta?

**Cada domingo a las 10:00 AM (Chile)**

Próximas ejecuciones:
- 2025-11-17 (domingo) - Semana 1
- 2025-11-24 (domingo) - Semana 2
- 2025-12-01 (domingo) - **Semana 3 (MILESTONE - 21 días de datos)**

---

## 📋 Configuración Técnica

### Cron Job

```bash
# Configurado en: crontab del servidor
0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh >> /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log 2>&1
```

**Verificar configuración:**
```bash
ssh reporting "crontab -l | grep copper"
```

### Scripts Involucrados

1. **`scripts/weekly_copper_tracking.sh`** (wrapper de automatización)
   - Calcula días desde integración
   - Ejecuta script de tracking
   - Genera logs detallados
   - Detecta milestones (7, 14, 21 días)
   - Limpia reportes antiguos

2. **`scripts/track_copper_impact.py`** (core logic)
   - Carga predictions desde parquet
   - Separa datos pre/post copper
   - Calcula métricas por horizonte
   - Genera reportes JSON y HTML

---

## 📊 Archivos Generados Automáticamente

### Reportes (cada domingo)

```
output/
├── copper_impact_report_20251117_100000.html  (Semana 1)
├── copper_impact_report_20251124_100000.html  (Semana 2)
├── copper_impact_report_20251201_100000.html  (Semana 3) ← MILESTONE
└── ...
```

**Cleanup automático:** Solo mantiene últimos 10 reportes

### Logs

```
logs/
├── copper_tracking.log            (log detallado del script)
└── copper_tracking_cron.log       (log de ejecución cron)
```

---

## 🔍 Cómo Revisar los Reportes

### Opción 1: Ver en Servidor

```bash
# Listar reportes disponibles
ssh reporting "ls -lht /home/deployer/forex-forecast-system/output/copper_impact_report_*.html | head -5"

# Ver último log
ssh reporting "tail -50 /home/deployer/forex-forecast-system/logs/copper_tracking.log"
```

### Opción 2: Descargar y Ver Localmente (Recomendado)

```bash
# Descargar reporte más reciente
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.html output/

# Abrir en navegador
open output/copper_impact_report_*.html  # macOS
```

---

## 📈 Timeline de Análisis

### Semana 1 (2025-11-17)

**Días de datos:** 4 días (desde 2025-11-13)

**Estado esperado:** INSUFFICIENT_DATA

**Mensaje en log:**
```
ℹ️  Insufficient data for analysis. Report generated but awaiting more data.
```

**Acción:** Ninguna, esperar más datos

---

### Semana 2 (2025-11-24)

**Días de datos:** 11 días

**Estado esperado:** PARTIAL_DATA o INSUFFICIENT_DATA

**Mensaje en log:**
```
📊 Week 2 report generated. Continue monitoring.
```

**Acción:** Revisar reporte, tendencias empiezan a ser visibles

---

### Semana 3 (2025-12-01) - **MILESTONE**

**Días de datos:** 18 días

**Estado esperado:** SUFFICIENT_DATA para decisión

**Mensaje en log:**
```
🎯 MILESTONE REACHED: 3 weeks of data collected
📌 ACTION REQUIRED: Review copper impact report and make GO/NO-GO decision
```

**Acción:** **REVISAR REPORTE Y TOMAR DECISIÓN GO/NO-GO**

---

## 🎯 Criterios de Decisión (Semana 3)

### SUCCESS (GO para siguiente fase)

**Si el reporte muestra:**
- ✅ RMSE improvement >= -15%
- ✅ >= 3 de 4 horizontes mejorados
- ✅ Directional accuracy >= 60%

**Acción:**
➡️ Continuar con **Fase 2: Treasury Yields + IPSA**

---

### PARTIAL SUCCESS (Esperar o ajustar)

**Si el reporte muestra:**
- ⚠️ RMSE improvement entre -5% y -15%
- ⚠️ 2 de 4 horizontes mejorados
- ⚠️ Directional accuracy 55-60%

**Acción:**
➡️ Esperar 1 semana más o proceder con cautela

---

### NO IMPROVEMENT (Investigar)

**Si el reporte muestra:**
- ❌ RMSE improvement < -5%
- ❌ < 2 horizontes mejorados
- ❌ Directional accuracy < 55%

**Acción:**
➡️ Investigar causas:
- ¿Datos de copper llegando correctamente?
- ¿Features bien calculadas?
- ¿Correlación copper-USD/CLP se mantiene?

---

## 🔧 Comandos Útiles

### Verificar que Cron Está Activo

```bash
# Ver configuración de cron
ssh reporting "crontab -l | grep copper"

# Ver última ejecución
ssh reporting "tail -20 /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log"
```

### Ejecutar Manualmente (Fuera de Schedule)

```bash
# Si necesitas un reporte antes del domingo
ssh reporting "/home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh"
```

### Ver Histórico de Ejecuciones

```bash
# Ver todas las ejecuciones
ssh reporting "grep 'WEEKLY COPPER TRACKING' /home/deployer/forex-forecast-system/logs/copper_tracking.log"

# Ver solo milestones detectados
ssh reporting "grep 'MILESTONE' /home/deployer/forex-forecast-system/logs/copper_tracking.log"
```

### Descargar Todos los Reportes

```bash
# Descargar todos para análisis comparativo
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.html output/
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.json output/
```

---

## 📧 Notificación Automática ✅ IMPLEMENTADO

El script **ENVÍA EMAILS AUTOMÁTICAMENTE** cada vez que ejecuta.

**Destinatario:** rafael@cavara.cl (responsable de optimización)

**Contenido del email:**
- Subject dinámico basado en semana y status
- Resumen ejecutivo en HTML (inline)
- Tabla de análisis por horizonte
- Reporte HTML completo adjunto
- Banner especial cuando días >= 21 (MILESTONE)

**Archivos involucrados:**
- `scripts/send_copper_report_email.py` (445 líneas) - Script de envío
- `scripts/weekly_copper_tracking.sh` (llama al script de email)

**Ejemplo de subject:**
```
Semana 1-2: "ℹ️ Copper Impact Report - Semana 1 - INSUFFICIENT DATA"
Semana 3+: "🎯 MILESTONE: Copper Impact Report - Semana 3 - ACCIÓN REQUERIDA"
```

**Test exitoso:** 2025-11-14 00:01:33 - Email enviado correctamente

---

## 🛠️ Troubleshooting

### Problema: Cron No Ejecuta

**Diagnóstico:**
```bash
# Verificar que cron está configurado
ssh reporting "crontab -l"

# Verificar permisos del script
ssh reporting "ls -la /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh"
```

**Solución:**
```bash
# Reconfigurar cron
ssh reporting "crontab -e"
# Agregar línea:
# 0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh >> /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log 2>&1
```

---

### Problema: Script Falla

**Diagnóstico:**
```bash
# Ver error en logs
ssh reporting "tail -100 /home/deployer/forex-forecast-system/logs/copper_tracking.log"
```

**Causas comunes:**
- Python3 no encontrado: Verificar path en script
- Predictions.parquet no existe: Forecasters no han ejecutado
- Permisos insuficientes: `chmod +x weekly_copper_tracking.sh`

---

### Problema: No Hay Reportes

**Diagnóstico:**
```bash
# Verificar que script se ejecutó
ssh reporting "ls -lht /home/deployer/forex-forecast-system/output/copper_impact_report_*.html"

# Verificar logs
ssh reporting "cat /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log"
```

**Solución:**
- Ejecutar manualmente para debug
- Verificar directorio output/ existe y tiene permisos

---

## 📅 Calendario de Ejecuciones (Próximas 4 Semanas)

| Fecha | Día | Ejecución | Días de Datos | Estado Esperado | Acción |
|-------|-----|-----------|---------------|-----------------|--------|
| 2025-11-17 | Dom | ✅ Auto | 4 | INSUFFICIENT_DATA | Ninguna |
| 2025-11-24 | Dom | ✅ Auto | 11 | INSUFFICIENT_DATA | Revisar tendencias |
| 2025-12-01 | Dom | ✅ Auto | 18 | PARTIAL_DATA | Análisis parcial |
| 2025-12-08 | Dom | ✅ Auto | 25 | **SUFFICIENT_DATA** | **DECISIÓN GO/NO-GO** |

**Nota:** La fecha clave es **2025-12-08** (no 2025-12-04 como se pensaba inicialmente) porque necesitamos >= 21 días de datos.

---

## ✅ Checklist de Verificación

- [x] Cron job configurado en servidor
- [x] Script ejecutable (`chmod +x`)
- [x] Directorio de logs existe
- [x] Directorio de output existe
- [x] Test manual ejecutado exitosamente
- [x] Próxima ejecución confirmada: 2025-11-17 10:00

---

## 🎯 Próximos Pasos

1. **2025-11-17:** Primera ejecución automática
2. **2025-11-24:** Segunda ejecución automática
3. **2025-12-01:** Tercera ejecución automática
4. **2025-12-08:** Cuarta ejecución (>21 días) → **MILESTONE**
5. **2025-12-08:** Revisar reporte y decidir próxima fase

**No se requiere acción manual hasta el 2025-12-08.**

---

**Última actualización:** 2025-11-13 23:55 (Chile)
**Estado:** ✅ AUTOMATIZADO Y OPERACIONAL
**Próxima ejecución:** 2025-11-17 10:00 (Chile)
