# USD/CLP Forecaster - Production Deployment Guide

## 🚀 Overview

Sistema de pronóstico USD/CLP desplegado en Vultr con ejecución automática diaria y recuperación automática ante fallas.

## 📋 Configuración de Producción

### Arquitectura
- **Servidor**: Vultr VPS
- **Containerización**: Docker + Docker Compose
- **Scheduler**: Cron dentro del contenedor
- **Auto-recovery**: Docker restart policy + systemd
- **Monitoring**: Docker healthcheck

### Componentes

#### 1. **Contenedor Docker** (`Dockerfile.7d.prod`)
- Base: Python 3.12-slim
- Incluye: cron, WeasyPrint dependencies
- Entrypoint: Script que inicia cron daemon
- Healthcheck: Verifica que cron esté funcionando

#### 2. **Cron Job** (`cron/7d/crontab`)
```cron
# Ejecuta pronóstico diario a las 8:00 AM Chile
0 8 * * * cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1

# Healthcheck cada hora
0 * * * * date > /tmp/healthcheck
```

#### 3. **Docker Compose** (`docker-compose.prod.yml`)
- Restart policy: `always` (se reinicia automáticamente)
- Volúmenes persistentes: data, reports, logs
- Variables de entorno desde `.env`
- Logging con rotación automática

#### 4. **Systemd Service** (`usdclp-forecaster.service`)
- Inicia automáticamente al arrancar el servidor
- Gestiona el ciclo de vida del contenedor
- Dependencia: docker.service

## 🔧 Comandos de Gestión

### Ver estado del servicio
```bash
docker ps | grep forecaster
docker logs usdclp-forecaster-7d
```

### Ver logs de cron
```bash
docker exec usdclp-forecaster-7d tail -f /var/log/cron.log
```

### Reiniciar el servicio
```bash
cd /home/deployer/forex-forecast-system
docker compose -f docker-compose.prod.yml restart forecaster-7d
```

### Detener el servicio
```bash
docker compose -f docker-compose.prod.yml down
```

### Rebuild y deploy
```bash
docker compose -f docker-compose.prod.yml build forecaster-7d
docker compose -f docker-compose.prod.yml up -d forecaster-7d
```

### Ejecutar manualmente (sin esperar al cron)
```bash
# Con email
docker exec usdclp-forecaster-7d python -m services.forecaster_7d.cli run

# Sin email (testing)
docker exec usdclp-forecaster-7d python -m services.forecaster_7d.cli run --skip-email
```

### Ver healthcheck status
```bash
docker inspect usdclp-forecaster-7d | grep -A 10 Health
```

## 🔄 Auto-Recovery

El sistema tiene múltiples capas de recuperación automática:

1. **Docker restart policy**: Si el contenedor falla, Docker lo reinicia automáticamente
2. **Systemd service**: Si el servidor se reinicia, systemd levanta el contenedor
3. **Healthcheck**: Docker monitorea que el cron esté funcionando correctamente
4. **Cron logging**: Todos los errores se registran en `/var/log/cron.log`

### Test de auto-recovery

```bash
# 1. Simular crash del contenedor
docker kill usdclp-forecaster-7d

# 2. Verificar que se reinicia automáticamente (esperar ~5 segundos)
docker ps | grep forecaster
# Debe mostrar: Up X seconds (health: starting)

# 3. Verificar logs
docker logs usdclp-forecaster-7d
```

## 📊 Monitoring

### Verificar última ejecución
```bash
# Ver último reporte generado
ls -lth /home/deployer/forex-forecast-system/reports/ | head -5

# Ver logs del último cron job
docker exec usdclp-forecaster-7d tail -100 /var/log/cron.log
```

### Email notifications
Los reportes se envían automáticamente a:
- Destinatarios configurados en `EMAIL_RECIPIENTS` (variable de entorno en `.env`)

## 🛠️ Troubleshooting

### El cron no se ejecuta
```bash
# Verificar que el crontab esté instalado
docker exec usdclp-forecaster-7d crontab -l

# Verificar que cron daemon esté corriendo
docker exec usdclp-forecaster-7d ps aux | grep cron

# Ver logs de cron
docker exec usdclp-forecaster-7d tail -f /var/log/cron.log
```

### El contenedor no se reinicia automáticamente
```bash
# Verificar systemd service
sudo systemctl status usdclp-forecaster.service

# Si está fallando, reiniciar
sudo systemctl restart usdclp-forecaster.service

# Ver logs de systemd
sudo journalctl -u usdclp-forecaster.service -f
```

### Emails no llegan
```bash
# Ejecutar manualmente y ver logs
docker exec usdclp-forecaster-7d python -m services.forecaster_7d.cli run

# Verificar variables de entorno
docker exec usdclp-forecaster-7d env | grep -E "GMAIL|EMAIL"

# Ver logs de envío
docker logs usdclp-forecaster-7d | grep -i email
```

## 📝 Variables de Entorno Requeridas

Configuradas en `/home/deployer/forex-forecast-system/.env`:

```env
# APIs
FRED_API_KEY=your_fred_api_key
NEWS_API_KEY=your_news_api_key

# Email (Gmail)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_specific_password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com

# Environment
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago
```

## 🔐 Seguridad

- ✅ `.env` montado como read-only
- ✅ Logs con rotación automática (max 10MB, 3 archivos)
- ✅ Contenedor ejecuta con usuario no-root (donde sea posible)
- ✅ Variables sensibles no se loggean

## 📅 Schedule

**Ejecución diaria**:
- Hora: 08:00 AM (Chile, UTC-3)
- Frecuencia: Todos los días
- Duración típica: ~15-20 segundos
- Output: PDF + Email notification

## ✅ Status Actual

- ✅ Contenedor: Running
- ✅ Cron: Configured (8:00 AM daily)
- ✅ Healthcheck: Active
- ✅ Auto-restart: Enabled
- ✅ Systemd: Enabled
- ✅ Email: Working
- ✅ Correlation Matrix: Fixed (timezone normalization)

## 📞 Contacto y Soporte

Para cualquier issue o pregunta:
1. Revisar logs: `docker logs usdclp-forecaster-7d`
2. Revisar cron logs: `docker exec usdclp-forecaster-7d tail -100 /var/log/cron.log`
3. Verificar reportes: `ls -lth /home/deployer/forex-forecast-system/reports/`

---

**Última actualización**: 2025-11-13
**Versión**: 1.0.0 (Production)
**Servidor**: Vultr VPS
