# 🚀 Sistema USD/CLP Desplegado en Vultr

**Fecha de despliegue**: 2025-11-12
**Estado**: ✅ ACTIVO Y AUTOMATIZADO
**Servidor**: Vultr VPS (ssh reporting)

---

## 📍 Ubicación del Proyecto

```bash
/home/deployer/forex-forecast-system/
├── src/                    # Código fuente
├── venv/                   # Entorno virtual Python
├── data/                   # Caché de datos históricos
├── reports/                # PDFs generados
├── logs/                   # Logs de ejecución
├── run_7d_forecast.sh      # Script de ejecución automática
├── .env                    # Variables de entorno
└── DEPLOYMENT_INFO.md      # Este documento
```

---

## ⚙️ Configuración Automática (Cron)

### Ejecución Programada

**Pronóstico 7 días**: 
- **Horario**: Todos los días a las 8:00 AM (hora Chile, UTC-3)
- **Script**: `/home/deployer/forex-forecast-system/run_7d_forecast.sh`
- **Log principal**: `/home/deployer/forex-forecast-system/logs/cron_7d.log`
- **Logs individuales**: `/home/deployer/forex-forecast-system/logs/forecast_7d_YYYYMMDD_HHMMSS.log`

### Limpieza Automática

- **Logs antiguos**: Se eliminan después de 30 días (diariamente a medianoche)
- **PDFs antiguos**: Se eliminan después de 90 días (diariamente a medianoche)

### Ver Configuración Actual

```bash
crontab -l
```

---

## 🔧 Ejecución Manual

### Ejecutar Pronóstico Ahora

```bash
cd /home/deployer/forex-forecast-system
./run_7d_forecast.sh
```

### Ver Logs en Tiempo Real

```bash
tail -f /home/deployer/forex-forecast-system/logs/cron_7d.log
```

### Ver Último Log Detallado

```bash
ls -t /home/deployer/forex-forecast-system/logs/forecast_7d_*.log | head -1 | xargs cat
```

---

## 📊 Salidas del Sistema

### PDFs Generados

**Ubicación**: `/home/deployer/forex-forecast-system/reports/`
**Formato**: `usdclp_report_7d_YYYYMMDD_HHMM.pdf`
**Tamaño típico**: ~260 KB

### Descargar Último PDF

```bash
# Desde tu máquina local
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_$(date +%Y%m%d)*.pdf ~/Downloads/
```

---

## 🐳 Alternativa: Ejecución con Docker

Si prefieres usar Docker en lugar de cron directo:

```bash
cd /home/deployer/forex-forecast-system

# Build imágenes
docker-compose build

# Ejecutar servicio 7d
docker-compose run --rm forecaster-7d

# Ver logs
docker-compose logs -f forecaster-7d
```

---

## 📈 Monitoreo

### Verificar Estado del Sistema

```bash
# ¿Está corriendo cron?
systemctl status cron

# ¿Cuándo fue la última ejecución?
ls -lth /home/deployer/forex-forecast-system/reports/ | head -5

# ¿Hay errores recientes?
tail -50 /home/deployer/forex-forecast-system/logs/cron_7d.log
```

### Verificar Uso de Recursos

```bash
# Espacio en disco
df -h /home/deployer/forex-forecast-system

# Tamaño de datos cacheados
du -sh /home/deployer/forex-forecast-system/data/

# Tamaño de reports
du -sh /home/deployer/forex-forecast-system/reports/
```

---

## 🔑 Variables de Entorno

**Archivo**: `/home/deployer/forex-forecast-system/.env`

```bash
FRED_API_KEY=861f53357ec653b2968c6cb6a25aafbf
NEWS_API_KEY=4194ecbae8294319996a280e793b450f
GMAIL_USER=rafaelfariaspoblete@gmail.com
GMAIL_APP_PASSWORD=ucbaypqpvpvpiqwqxg
EMAIL_RECIPIENTS=["rafael@cavara.cl","valentina@cavara.cl"]
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago
```

---

## 🛠️ Mantenimiento

### Actualizar Código desde GitHub

```bash
cd /home/deployer/forex-forecast-system
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Limpiar Caché de Datos

```bash
rm -rf /home/deployer/forex-forecast-system/data/warehouse/*
# Los datos se volverán a descargar en la próxima ejecución
```

### Reiniciar Servicio Cron

```bash
sudo systemctl restart cron
```

---

## 🆘 Troubleshooting

### El PDF no se generó

1. Verificar logs:
```bash
tail -100 /home/deployer/forex-forecast-system/logs/cron_7d.log
```

2. Ejecutar manualmente para ver errores:
```bash
cd /home/deployer/forex-forecast-system
./run_7d_forecast.sh
```

### Error de API Keys

Verificar que las API keys sean válidas:
```bash
cat /home/deployer/forex-forecast-system/.env
```

### Error de WeasyPrint

Reinstalar dependencias del sistema:
```bash
sudo apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

### Cron no ejecuta

Verificar sintaxis de crontab:
```bash
crontab -l
```

Ver logs del sistema:
```bash
sudo tail -f /var/log/syslog | grep CRON
```

---

## 📞 Información de Contacto

**GitHub Repository**: https://github.com/Pit-CL/forex-forecast-system
**Servidor**: Vultr VPS
**SSH Alias**: `ssh reporting`
**Usuario**: deployer

---

## 📅 Próximos Pasos (Opcional)

- [ ] Configurar alertas por email cuando falle una ejecución
- [ ] Agregar dashboard web para visualizar histórico de pronósticos
- [ ] Implementar pronóstico 12 meses (actualmente solo 7 días)
- [ ] Configurar backup automático de PDFs a S3/Cloud Storage
- [ ] Implementar API REST para consultar pronósticos
- [ ] Agregar notificaciones por Slack/Telegram

---

**Última actualización**: 2025-11-12 14:58
**Generado por**: Claude Code
