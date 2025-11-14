# Host Cron Cleanup Plan - Vultr Reporting Server

## Estado Actual (Detectado en servidor)

```cron
# 1. Limpieza de logs (MANTENER)
0 0 * * * find /home/deployer/forex-forecast-system/logs -name "forecast_7d_*.log" -mtime +30 -delete 2>&1
0 0 * * * find /home/deployer/forex-forecast-system/reports -name "usdclp_*.pdf" -mtime +90 -delete 2>&1

# 2. Chronos Readiness Check (ELIMINAR - Chronos obsoleto)
0 9 * * * cd /home/deployer/forex-forecast-system && bash scripts/daily_readiness_check.sh >> /home/deployer/forex-forecast-system/logs/readiness_checks.log 2>&1

# 3. Docker cleanup (MANTENER - Mantenimiento sistema)
0 2 * * * cd /home/deployer/forex-forecast-system && bash scripts/auto_cleanup_docker.sh >> /home/deployer/forex-forecast-system/logs/docker_cleanup.log 2>&1

# 4. Weekly validation (ELIMINAR - Debe estar en Docker)
0 9 * * 1 cd /home/deployer/forex-forecast-system && ./scripts/weekly_validation.sh >> /home/deployer/forex-forecast-system/logs/cron.log 2>&1

# 5. Unified daily email (ELIMINAR - Reemplazar con estrategia optimizada en Docker)
30 7 * * 1,3,4,5 cd /home/deployer/forex-forecast-system && ./scripts/send_daily_email.sh >> /home/deployer/forex-forecast-system/logs/cron.log 2>&1

# 6. Performance check (ELIMINAR - Debe estar en Docker)
0 10 * * * cd /home/deployer/forex-forecast-system && python scripts/check_performance.py --all >> /home/deployer/forex-forecast-system/logs/cron.log 2>&1

# 7. Copper tracking (ELIMINAR - Debe estar en Docker)
0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh >> /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log 2>&1
```

---

## Decisiones de Cleanup

### ✅ MANTENER EN HOST (2 crons)

#### 1. Limpieza de Logs y Reportes
```cron
0 0 * * * find /home/deployer/forex-forecast-system/logs -name "forecast_7d_*.log" -mtime +30 -delete
0 0 * * * find /home/deployer/forex-forecast-system/reports -name "usdclp_*.pdf" -mtime +90 -delete
```

**Por qué mantener**:
- Gestión de espacio en disco del HOST
- Los contenedores Docker escriben logs/reportes en volúmenes montados
- Debe ejecutarse a nivel de sistema operativo, no dentro de contenedor
- Previene llenar disco (crítico para estabilidad)

#### 2. Docker Cleanup
```cron
0 2 * * * cd /home/deployer/forex-forecast-system && bash scripts/auto_cleanup_docker.sh >> logs/docker_cleanup.log 2>&1
```

**Por qué mantener**:
- Gestión de recursos Docker (imágenes huérfanas, volúmenes sin usar)
- Debe ejecutarse desde HOST para administrar Docker daemon
- Previene acumulación de imágenes antiguas (>85% disco)

---

### ❌ ELIMINAR DEL HOST (5 crons)

#### 3. Chronos Readiness Check
```cron
0 9 * * * cd /home/deployer/forex-forecast-system && bash scripts/daily_readiness_check.sh
```

**Por qué eliminar**:
- ❌ Chronos será removido del sistema (migración a XGBoost+SARIMAX+GARCH)
- ❌ Script obsoleto
- ❌ No aplica al nuevo sistema de modelos interpretables

**Acción**: Eliminar cron + eliminar script `scripts/daily_readiness_check.sh`

#### 4. Weekly Validation
```cron
0 9 * * 1 cd /home/deployer/forex-forecast-system && ./scripts/weekly_validation.sh
```

**Por qué eliminar**:
- ❌ Validación debe ser responsabilidad del contenedor que genera forecast
- ❌ No hay visibilidad dentro del contenedor si se ejecuta desde host
- ✅ MIGRAR: Walk-forward validation dentro de auto-retraining scripts (ya implementado)

**Acción**: Eliminar cron (validación ya está en `auto_retrain_xgboost.py` y `auto_retrain_sarimax.py`)

#### 5. Unified Daily Email ⚠️ CRÍTICO
```cron
30 7 * * 1,3,4,5 cd /home/deployer/forex-forecast-system && ./scripts/send_daily_email.sh
```

**Por qué eliminar del host**:
- ❌ Vieja estrategia (7:30 AM lun/mié/jue/vie) no optimizada
- ❌ No sigue principio Docker-first
- ✅ REEMPLAZAR: Nueva estrategia de @agent-usdclp (ver `OPTIMAL_CRON_STRATEGY.md`)

**Acción**:
1. Eliminar este cron del host
2. Implementar nuevos crons optimizados DENTRO de Docker (estrategia de mercado)
3. Emails enviados desde contenedores según horario estratégico

#### 6. Performance Check
```cron
0 10 * * * cd /home/deployer/forex-forecast-system && python scripts/check_performance.py --all
```

**Por qué eliminar**:
- ❌ Debe ejecutarse dentro del contenedor que tiene contexto del modelo
- ❌ No tiene acceso a métricas internas del contenedor desde host
- ✅ MIGRAR: Integrado en `ModelPerformanceMonitor` (ya implementado)

**Acción**: Eliminar cron (monitoreo ya está en sistema de alertas)

#### 7. Weekly Copper Tracking
```cron
0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh
```

**Por qué eliminar**:
- ❌ Tracking de copper debe ser parte del sistema de features
- ❌ No necesita cron separado (feature engineering lo maneja)
- ✅ YA IMPLEMENTADO: Copper features en `feature_engineer.py`

**Acción**: Eliminar cron (copper tracking integrado en forecasting)

---

## Nueva Arquitectura (Docker-First)

### HOST (Solo 2 crons de infraestructura)
```cron
# Limpieza de logs (30 días)
0 0 * * * find /home/deployer/forex-forecast-system/logs -name "*.log" -mtime +30 -delete

# Limpieza de reportes (90 días)
0 0 * * * find /home/deployer/forex-forecast-system/reports -name "*.pdf" -mtime +90 -delete

# Docker cleanup cuando uso >85%
0 2 * * * cd /home/deployer/forex-forecast-system && bash scripts/auto_cleanup_docker.sh >> logs/docker_cleanup.log 2>&1
```

### DOCKER CONTAINERS (Toda la lógica de aplicación)

**Container 7d** (`cron/7d/crontab.optimized`):
```cron
# Forecasts: Lunes, Miércoles, Viernes a las 7:00 AM Chile
0 7 * * 1,3,5 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 7

# Email: 7:30 AM después de forecast
30 7 * * 1,3,5 cd /app && PYTHONPATH=/app/src python /app/scripts/send_daily_email.sh --horizon 7d

# Re-training: Domingo 00:00
0 0 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 7
```

**Container 15d** (`cron/15d/crontab.optimized`):
```cron
# Forecast: Lunes y Jueves 7:00 AM
0 7 * * 1,4 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 15

# Email: 7:30 AM después de forecast
30 7 * * 1,4 cd /app && PYTHONPATH=/app/src python /app/scripts/send_daily_email.sh --horizon 15d

# Re-training: Domingo 00:00
0 0 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 15
```

**Container 30d** (`cron/30d/crontab.optimized`):
```cron
# Forecast: Jueves 1 y 15 + Viernes 7:00 AM
0 7 1,15 * 4 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 30
0 7 * * 5 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 30

# Email: 7:30 AM después de forecast
30 7 1,15 * 4 cd /app && PYTHONPATH=/app/src python /app/scripts/send_daily_email.sh --horizon 30d
30 7 * * 5 cd /app && PYTHONPATH=/app/src python /app/scripts/send_daily_email.sh --horizon 30d

# Re-training: Domingo 00:00 (XGBoost), 1ro de mes (SARIMAX)
0 0 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 30
0 1 1 * * cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_sarimax.py --horizon 30
```

**Container 90d** (`cron/90d/crontab.optimized`):
```cron
# Forecast: Primer martes del mes 7:00 AM
0 7 1-7 * 2 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 90

# Email: 7:30 AM después de forecast
30 7 1-7 * 2 cd /app && PYTHONPATH=/app/src python /app/scripts/send_daily_email.sh --horizon 90d

# Re-training: Domingo 00:00 (XGBoost), 1ro de mes (SARIMAX)
0 0 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 90
0 1 1 * * cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_sarimax.py --horizon 90
```

---

## Plan de Ejecución

### Paso 1: Backup del Crontab Actual
```bash
ssh reporting "crontab -l > ~/crontab_backup_$(date +%Y%m%d).txt"
```

### Paso 2: Crear Nuevo Crontab (Solo Infraestructura)
```bash
ssh reporting "cat > /tmp/new_crontab <<'EOF'
# USD/CLP Forex System - Host Infrastructure Only
# Application logic runs inside Docker containers

# Log cleanup (30 days retention)
0 0 * * * find /home/deployer/forex-forecast-system/logs -name "*.log" -mtime +30 -delete 2>&1

# Report cleanup (90 days retention)
0 0 * * * find /home/deployer/forex-forecast-system/reports -name "*.pdf" -mtime +90 -delete 2>&1

# Docker cleanup (when disk usage >= 85%)
0 2 * * * cd /home/deployer/forex-forecast-system && bash scripts/auto_cleanup_docker.sh >> logs/docker_cleanup.log 2>&1
EOF
"
```

### Paso 3: Aplicar Nuevo Crontab
```bash
ssh reporting "crontab /tmp/new_crontab"
```

### Paso 4: Verificar
```bash
ssh reporting "crontab -l"
```

### Paso 5: Aplicar Crons Optimizados en Docker
```bash
# Copiar crontabs optimizados a contenedores (ya implementado en archivos .optimized)
# Se aplicarán en el próximo rebuild de Docker images
```

---

## Verificación Post-Cleanup

### Check 1: Host Crontab
```bash
ssh reporting "crontab -l | wc -l"  # Debe mostrar 3 líneas
```

### Check 2: Docker Cron Logs
```bash
ssh reporting "docker logs forex-7d | grep cron"
ssh reporting "docker logs forex-15d | grep cron"
ssh reporting "docker logs forex-30d | grep cron"
ssh reporting "docker logs forex-90d | grep cron"
```

### Check 3: Email Delivery Test
```bash
# Esperar al próximo horario programado y verificar recepción
```

---

## Rollback Plan

Si algo falla:

```bash
# Restaurar crontab anterior
ssh reporting "crontab ~/crontab_backup_YYYYMMDD.txt"

# Verificar
ssh reporting "crontab -l"
```

---

## Resumen de Cambios

| Cron | Estado Actual | Acción | Nueva Ubicación |
|------|---------------|---------|------------------|
| Limpieza logs | Host | ✅ MANTENER | Host (infraestructura) |
| Docker cleanup | Host | ✅ MANTENER | Host (infraestructura) |
| Chronos readiness | Host | ❌ ELIMINAR | N/A (obsoleto) |
| Weekly validation | Host | ❌ ELIMINAR | Docker (auto-retraining) |
| Daily email | Host | ❌ ELIMINAR | Docker (estrategia optimizada) |
| Performance check | Host | ❌ ELIMINAR | Docker (ModelPerformanceMonitor) |
| Copper tracking | Host | ❌ ELIMINAR | Docker (feature_engineer) |

**Total**: 7 crons → 3 crons (reducción 57%)

---

## Beneficios del Cambio

1. ✅ **Replicabilidad**: Todo el código de aplicación en Docker (versionado en Git)
2. ✅ **Mantenibilidad**: Cambios de crons via Git, no SSH al servidor
3. ✅ **Testabilidad**: Crons probables localmente en Docker
4. ✅ **Portabilidad**: Sistema funciona en cualquier servidor con Docker
5. ✅ **Separación**: Infraestructura (host) vs. Aplicación (Docker)
6. ✅ **Optimización**: Nueva estrategia de @agent-usdclp (basada en mercado)

---

**Preparado por**: @agent-usdclp + Claude Code
**Fecha**: 14 Noviembre 2025
**Estado**: LISTO PARA EJECUCIÓN
