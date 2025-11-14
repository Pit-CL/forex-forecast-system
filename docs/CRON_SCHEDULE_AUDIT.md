# 📅 Auditoría Completa de Cron Jobs - Sistema Forex USD/CLP

**Fecha de Auditoría:** 2025-11-13
**Servidor:** Vultr VPS (155.138.162.47)
**Timezone:** America/Santiago (Chile)

---

## 🏗️ Arquitectura del Sistema

El sistema utiliza una arquitectura híbrida:
- **Crons del Host (Vultr):** Gestión, validación, emails, cleanup
- **Crons en Docker:** Generación de pronósticos dentro de containers

---

## 📊 HOST SYSTEM CRONS (Vultr Server)

### Ubicación
```
Usuario: root
Archivo: /var/spool/cron/crontabs/root
```

### Jobs Configurados

| Horario | Frecuencia | Comando | Propósito | Status |
|---------|-----------|---------|-----------|--------|
| **00:00** | Diario | `find logs -name "forecast_7d_*.log" -mtime +30 -delete` | Limpieza de logs antiguos (>30 días) | ✅ Activo |
| **00:00** | Diario | `find reports -name "usdclp_*.pdf" -mtime +90 -delete` | Limpieza de PDFs antiguos (>90 días) | ✅ Activo |
| **02:00** | Diario | `./scripts/auto_cleanup_docker.sh` | Limpieza Docker si disk usage ≥85% | ✅ Activo |
| **07:30** | Lun/Mié/Jue/Vie | `./scripts/send_daily_email.sh` | **Email unificado con pronósticos** | ✅ Activo |
| **09:00** | Diario | `./scripts/daily_readiness_check.sh` | Chequeo Chronos readiness | ✅ Activo |
| **09:00** | Lunes | `./scripts/weekly_validation.sh` | Validación semanal de modelos | ✅ Activo |
| **10:00** | Diario | `python scripts/check_performance.py --all` | Chequeo de performance | ✅ Activo |

### Logs
```
/home/deployer/forex-forecast-system/logs/cron.log
/home/deployer/forex-forecast-system/logs/readiness_checks.log
/home/deployer/forex-forecast-system/logs/docker_cleanup.log
```

---

## 🐳 DOCKER CONTAINER CRONS

### Container: forecaster-7d (Pronóstico 7 días)

**Image:** `forex-forecast-system-forecaster-7d`
**Status:** ✅ Running (Healthy)

| Horario | Frecuencia | Comando | Propósito |
|---------|-----------|---------|-----------|
| **08:00** | Diario | `python -m services.forecaster_7d.cli run` | Generar pronóstico 7 días |
| **XX:00** | Cada hora | `date > /tmp/healthcheck` | Health check del container |

**Output:** `/var/log/cron.log` (dentro del container)
**PDF Generado:** `/home/deployer/forex-forecast-system/reports/usdclp_forecast_7d_YYYY-MM-DD.pdf`

---

### Container: forecaster-15d (Pronóstico 15 días)

**Image:** `forex-forecast-system-forecaster-15d`
**Status:** ✅ Running (Healthy)

| Horario | Frecuencia | Comando | Propósito |
|---------|-----------|---------|-----------|
| **09:00** | Días 1 y 15 | `python -m services.forecaster_15d.cli run` | Generar pronóstico 15 días |
| **XX:00** | Cada hora | `date > /tmp/healthcheck` | Health check del container |

**Output:** `/var/log/cron.log` (dentro del container)
**PDF Generado:** `/home/deployer/forex-forecast-system/reports/usdclp_forecast_15d_YYYY-MM-DD.pdf`

---

### Container: forecaster-30d (Pronóstico 30 días)

**Image:** `forex-forecast-system-forecaster-30d`
**Status:** ✅ Running (Healthy)

| Horario | Frecuencia | Comando | Propósito |
|---------|-----------|---------|-----------|
| **09:30** | Día 1 de cada mes | `python -m services.forecaster_30d.cli run` | Generar pronóstico 30 días |
| **XX:00** | Cada hora | `date > /tmp/healthcheck` | Health check del container |

**Output:** `/var/log/cron.log` (dentro del container)
**PDF Generado:** `/home/deployer/forex-forecast-system/reports/usdclp_forecast_30d_YYYY-MM-DD.pdf`

---

### Container: forecaster-90d (Pronóstico 90 días)

**Image:** `forex-forecast-system-forecaster-90d`
**Status:** ✅ Running (Healthy)

| Horario | Frecuencia | Comando | Propósito |
|---------|-----------|---------|-----------|
| **10:00** | Día 1 trimestral (Ene/Abr/Jul/Oct) | `python -m services.forecaster_90d.cli run` | Generar pronóstico 90 días |
| **XX:00** | Cada hora | `date > /tmp/healthcheck` | Health check del container |

**Output:** `/var/log/cron.log` (dentro del container)
**PDF Generado:** `/home/deployer/forex-forecast-system/reports/usdclp_forecast_90d_YYYY-MM-DD.pdf`

---

## 📅 CRONOGRAMA VISUAL - SEMANA TÍPICA

### Lunes
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
07:30 - 📧 Email unificado (7d + 15d)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check + Weekly validation
10:00 - Performance check
```

### Martes
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
```

### Miércoles
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
07:30 - 📧 Email unificado (7d solamente)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
```

### Jueves
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
07:30 - 📧 Email unificado (15d solamente)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
```

### Viernes
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
07:30 - 📧 Email unificado (7d + 30d + resumen semanal)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
```

### Sábado
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
(NO se envía email)
```

### Domingo
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker (si disk >85%)
08:00 - 🔮 Pronóstico 7d (container)
09:00 - Readiness check
10:00 - Performance check
(NO se envía email)
```

---

## 📅 EVENTOS ESPECIALES

### Día 1 del Mes
```
00:00 - Limpieza de logs y PDFs antiguos
02:00 - Auto cleanup Docker
07:30 - Email unificado (si es Lun/Mié/Jue/Vie)
08:00 - 🔮 Pronóstico 7d
09:00 - 🔮 Pronóstico 15d (quincenal)
09:30 - 🔮 Pronóstico 30d (mensual)
10:00 - Performance check

Si además es Enero/Abril/Julio/Octubre:
10:00 - 🔮 Pronóstico 90d (trimestral)
```

### Día 15 del Mes
```
(Cronograma normal del día de la semana)
09:00 - 🔮 Pronóstico 15d (quincenal adicional)
```

---

## 🔍 SCRIPTS VERIFICADOS

Todos los scripts referenciados en crons existen en el servidor:

### Scripts Shell (.sh)
- ✅ `auto_cleanup_docker.sh` (2.6K)
- ✅ `daily_dashboard.sh` (9.2K) - **DEPRECATED**
- ✅ `daily_readiness_check.sh` (1.9K)
- ✅ `install_cron_jobs.sh` (3.5K)
- ✅ `send_daily_email.sh` (5.9K)
- ✅ `test_unified_email.sh` (11K)
- ✅ `verify_deployment.sh` (6.9K)
- ✅ `weekly_validation.sh` (6.0K)

### Scripts Python (.py)
- ✅ `calibrate_usdclp.py` (16K)
- ✅ `check_chronos_readiness.py` (6.0K)
- ✅ `check_performance.py` (6.6K)
- ✅ `diagnose_ci_coverage.py` (10K)
- ✅ `mlops_dashboard.py` (16K)
- ✅ `validate_model.py` (11K)

---

## ⚠️ DEPRECATED SCRIPTS

### daily_dashboard.sh
**Status:** ⚠️ DEPRECATED
**Reemplazado por:** `send_daily_email.sh` (sistema unificado)
**Acción:** El script existe pero ya no está en crontab (correcto)

---

## 🎯 RESUMEN DE EJECUCIONES

### Frecuencia de Generación de Pronósticos

| Horizonte | Frecuencia | Ejecuciones/Mes | Ejecuciones/Año |
|-----------|-----------|-----------------|-----------------|
| **7d** | Diario | ~30 | ~365 |
| **15d** | Quincenal (días 1 y 15) | 2 | 24 |
| **30d** | Mensual (día 1) | 1 | 12 |
| **90d** | Trimestral (día 1) | 0.25 | 4 |

### Frecuencia de Emails

| Día | Horizonte incluidos | Ejecuciones/Mes | Ejecuciones/Año |
|-----|-------------------|-----------------|-----------------|
| **Lunes** | 7d + 15d | ~4 | ~52 |
| **Miércoles** | 7d | ~4 | ~52 |
| **Jueves** | 15d | ~4 | ~52 |
| **Viernes** | 7d + 30d | ~4 | ~52 |
| **Total** | - | ~16 | ~208 |

---

## 🔧 COMANDOS ÚTILES PARA MONITOREO

### Ver logs de cron del host
```bash
ssh reporting "tail -f /home/deployer/forex-forecast-system/logs/cron.log"
```

### Ver logs de container específico
```bash
ssh reporting "docker logs -f usdclp-forecaster-7d"
```

### Ver próximas ejecuciones de cron
```bash
ssh reporting "grep -v '^#' /var/spool/cron/crontabs/root | grep -v '^$'"
```

### Ver cron de un container
```bash
ssh reporting "docker exec usdclp-forecaster-7d crontab -l"
```

### Verificar estado de todos los containers
```bash
ssh reporting "docker ps -a | grep forecaster"
```

### Ver último forecast generado
```bash
ssh reporting "ls -lth /home/deployer/forex-forecast-system/reports/*.pdf | head -5"
```

---

## ✅ VALIDACIÓN DE CRONS

### Checklist de Validación

- [x] Todos los crons del host tienen scripts existentes
- [x] Todos los containers tienen crons configurados
- [x] No hay crons duplicados
- [x] Horarios optimizados (sin colisiones)
- [x] Logs configurados para todos los crons
- [x] Health checks en todos los containers
- [x] Scripts deprecated identificados y removidos de crontab
- [x] Email unificado reemplaza dashboard diario
- [x] Timezone configurado correctamente (America/Santiago)

---

## 🚨 ALERTAS Y CONSIDERACIONES

### Carga del Sistema

**Horario Pico: 07:30 - 10:00 AM**
- Envío de emails
- Generación de múltiples pronósticos
- Chequeos de performance

**Recomendación:** Monitorear recursos durante estas horas.

### Disk Space

- Limpieza automática de logs >30 días
- Limpieza automática de PDFs >90 días
- Auto cleanup Docker cuando disk >85%

**Recomendación:** Verificar disk space semanalmente.

### Health Checks

Todos los containers escriben `/tmp/healthcheck` cada hora.

**Verificar:** `docker ps` debería mostrar "(healthy)" para todos.

---

## 📞 TROUBLESHOOTING

### Si un cron no se ejecuta

1. Verificar logs: `/home/deployer/forex-forecast-system/logs/cron.log`
2. Verificar permisos del script: `ls -la scripts/`
3. Verificar cron service: `systemctl status cron`
4. Ejecutar manualmente para ver errores

### Si un container está unhealthy

1. Ver logs: `docker logs usdclp-forecaster-XX`
2. Verificar healthcheck: `docker inspect --format='{{.State.Health}}' usdclp-forecaster-XX`
3. Restart si necesario: `docker compose -f docker-compose.prod.yml restart forecaster-XX`

---

**Auditoría realizada:** 2025-11-13
**Sistema:** Production-ready ✅
**Próxima revisión recomendada:** 2025-12-13 (1 mes)
