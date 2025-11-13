# Deployment de Chronos en Producción

Guía paso a paso para habilitar Chronos-Bolt-Small en el sistema de forecasting USD/CLP en producción.

## Pre-requisitos

### 1. Recursos del Servidor

**Mínimos**:
- RAM: 4GB (al menos 1.5GB libre)
- CPU: 2 vCPUs
- Almacenamiento: +500MB para modelo
- Conexión a internet (primera descarga)

**Servidor actual (Vultr)**:
- ✅ RAM: 4GB
- ✅ CPU: 2 vCPUs AMD EPYC
- ✅ Almacenamiento: Suficiente
- ✅ Conexión: Disponible

### 2. Verificar Recursos Disponibles

```bash
# SSH al servidor
ssh user@your-server

# Verificar RAM disponible
free -h
# Debe mostrar al menos 1.5GB disponible

# Verificar espacio en disco
df -h
# Debe tener al menos 1GB libre en /
```

## Paso 1: Instalar Dependencias

### 1.1. Actualizar requirements.txt

El archivo `requirements.txt` ya incluye:
```
torch>=2.0.0
chronos-forecasting>=1.2.0
psutil>=5.9
```

### 1.2. Instalar en el Servidor

```bash
# SSH al servidor
cd /path/to/forex-forecast-system

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias (esto descargará ~2GB de paquetes)
pip install -r requirements.txt

# Verificar instalación
python -c "import chronos; print('Chronos OK')"
python -c "import torch; print(f'PyTorch {torch.__version__} OK')"
```

**Nota**: La primera instalación puede tomar 5-10 minutos dependiendo de la conexión.

### 1.3. Descargar Modelo (Opcional)

Para evitar descarga durante la primera ejecución en producción:

```bash
# Descargar modelo manualmente
python -c "from chronos import ChronosPipeline; ChronosPipeline.from_pretrained('amazon/chronos-bolt-small')"

# Esto descarga ~400MB y se cachea en ~/.cache/huggingface/
```

## Paso 2: Configuración por Servicio

### Opción A: Habilitar Globalmente (NO RECOMENDADO)

Modificar `.env`:
```bash
ENABLE_CHRONOS=true
```

Esto habilita Chronos en TODOS los servicios (7d, 15d, 30d, 90d).

⚠️ **No recomendado** para inicio, demasiado agresivo.

### Opción B: Habilitar por Servicio (RECOMENDADO)

Habilitar gradualmente empezando por forecaster_7d.

## Paso 3: Habilitar en forecaster_7d (Recomendado Primero)

### 3.1. Modificar Variables de Entorno

Crear/modificar `.env` para forecaster_7d:

```bash
# En el servidor
cd /path/to/forex-forecast-system/src/services/forecaster_7d

# Crear .env específico del servicio (opcional)
cat > .env << EOF
# Habilitar Chronos solo para 7d
ENABLE_CHRONOS=true

# Configuración de Chronos
CHRONOS_CONTEXT_LENGTH=180
CHRONOS_NUM_SAMPLES=100
EOF
```

### 3.2. Modificar docker-compose (si aplica)

Si usas Docker, modificar `docker-compose.yml`:

```yaml
services:
  forecaster_7d:
    environment:
      - ENABLE_CHRONOS=true
      - CHRONOS_CONTEXT_LENGTH=180
      - CHRONOS_NUM_SAMPLES=100
    # Asegurar suficiente memoria
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1.5G
```

### 3.3. Probar Localmente Primero

Antes de activar en producción, probar en servidor de desarrollo:

```bash
# Activar entorno
source venv/bin/activate

# Configurar variables
export ENABLE_CHRONOS=true
export CHRONOS_CONTEXT_LENGTH=180
export CHRONOS_NUM_SAMPLES=100

# Ejecutar forecaster manualmente
python -m services.forecaster_7d.pipeline

# Revisar logs
tail -f logs/forecaster_7d.log
```

Verificar en logs:
- ✅ "Loading Chronos pipeline"
- ✅ "Chronos inference completed in X.XXs"
- ✅ "Chronos pseudo-validation RMSE: X.XX"
- ✅ "Ensemble weights: {..., 'chronos': X.XX, ...}"

### 3.4. Activar en Producción

Una vez verificado:

```bash
# Rebuild Docker images (si aplica)
docker-compose build forecaster_7d

# Restart servicio
docker-compose restart forecaster_7d

# O si no usas Docker
systemctl restart forecaster_7d.service
```

### 3.5. Monitorear Primera Ejecución

```bash
# Ver logs en tiempo real
docker-compose logs -f forecaster_7d
# O
tail -f /var/log/forecaster_7d.log

# Monitorear uso de RAM
watch -n 1 'free -h'

# Monitorear uso de CPU
htop
```

**Qué esperar**:
- Primera ejecución: ~10-15s adicionales (descarga modelo)
- RAM peak: ~1-1.5GB durante inference
- CPU: 100% en 1 vCPU por ~3-5s
- Post-ejecución: RAM vuelve a nivel normal

## Paso 4: Validación Post-Deployment

### 4.1. Verificar Logs de Éxito

Buscar en logs:
```bash
grep "Chronos" /var/log/forecaster_7d.log
```

Debe mostrar:
```
[INFO] Running Chronos model (available RAM: XXXXMB)
[INFO] Chronos forecast: 7 steps, context=180, samples=100
[INFO] Chronos inference completed in X.XXs
[INFO] Chronos pseudo-validation RMSE: X.XXXX
[INFO] Chronos forecast complete: mean=XXX.XX, std=X.XX
```

### 4.2. Verificar Peso en Ensemble

```bash
grep "Ensemble weights" /var/log/forecaster_7d.log | tail -1
```

Debe incluir `'chronos': 0.XXX`

### 4.3. Revisar Reporte Generado

- Abrir último reporte PDF/HTML generado
- Verificar que metodología mencione Chronos
- Verificar que ensemble incluya Chronos en pesos

### 4.4. Verificar Métricas

```bash
# Ver últimas métricas
tail -5 /path/to/logs/metrics.jsonl | jq '.'
```

Debe incluir entrada para Chronos:
```json
{
  "timestamp": "2025-11-13T...",
  "models": {
    "arima_garch": {"RMSE": X.XX, "MAPE": X.XX},
    "var": {"RMSE": X.XX, "MAPE": X.XX},
    "chronos": {"RMSE": X.XX, "MAPE": X.XX}
  }
}
```

## Paso 5: Monitoreo Continuo (Primeras 2 Semanas)

### 5.1. Métricas a Monitorear

Crear dashboard o revisar semanalmente:

1. **Performance de Chronos**:
   - RMSE vs otros modelos
   - MAPE vs otros modelos
   - Peso en ensemble (idealmente 15-35%)

2. **Recursos del Sistema**:
   - Peak RAM usage durante forecast
   - Tiempo de ejecución total
   - Disponibilidad de RAM post-ejecución

3. **Estabilidad**:
   - Número de ejecuciones exitosas
   - Número de fallos de Chronos
   - Impacto en otros servicios

### 5.2. Alertas a Configurar

```bash
# Ejemplo: Alert si Chronos falla > 2 veces seguidas
grep "Chronos failed" /var/log/forecaster_7d.log | tail -10
```

### 5.3. Revisión Semanal

Checklist semanal:

- [ ] Chronos ejecutándose sin errores
- [ ] RAM peak < 3GB (dejar 1GB libre)
- [ ] Tiempo de ejecución < +10s vs sin Chronos
- [ ] Peso de Chronos entre 10-40%
- [ ] RMSE de Chronos competitivo con ARIMA/VAR
- [ ] Otros servicios no afectados

## Paso 6: Expansión Gradual (Opcional)

Una vez validado en forecaster_7d (2-4 semanas):

### 6.1. Habilitar en forecaster_15d

```bash
# Similar a forecaster_7d
cd /path/to/forex-forecast-system/src/services/forecaster_15d
echo "ENABLE_CHRONOS=true" >> .env
echo "CHRONOS_CONTEXT_LENGTH=180" >> .env

# Restart
docker-compose restart forecaster_15d
```

Monitorear 1-2 semanas.

### 6.2. Habilitar en forecaster_30d

```bash
cd /path/to/forex-forecast-system/src/services/forecaster_30d
echo "ENABLE_CHRONOS=true" >> .env
echo "CHRONOS_CONTEXT_LENGTH=90" >> .env  # 3 meses para 30d

docker-compose restart forecaster_30d
```

Monitorear 1-2 semanas.

### 6.3. Evaluar forecaster_90d

⚠️ **Precaución**: Chronos puede ser menos confiable en horizontes largos (90d).

**Criterio de activación**:
- Solo habilitar si Chronos demuestra RMSE < ARIMA en 7d/15d/30d
- Usar context_length=365 (1 año completo)
- Monitorear muy de cerca primeras ejecuciones

## Paso 7: Optimización (Después de 1 Mes)

### 7.1. Ajustar Hiperparámetros

Basado en métricas acumuladas, considerar:

**Si Chronos tiene peso bajo (<15%)**:
- Reducir `num_samples` a 50 (más rápido, menos overhead)
- O investigar por qué RMSE es alto

**Si Chronos es muy lento (>10s)**:
- Reducir `num_samples` a 75
- Reducir `context_length` (e.g., 180 → 120)

**Si Chronos es muy volátil**:
- Aumentar `num_samples` a 150
- Ajustar temperature (default 1.0 → 0.8)

### 7.2. Considerar GPU (Opcional)

Si se añade GPU al servidor:

```python
# Modificar chronos_model.py
device_map = "cuda" if torch.cuda.is_available() else "cpu"
```

Beneficio: 3-5x más rápido inference.

## Rollback en Caso de Problemas

### Si Chronos Causa Problemas

**Desactivar Inmediatamente**:

```bash
# Opción 1: Variable de entorno
export ENABLE_CHRONOS=false

# Opción 2: Modificar .env
sed -i 's/ENABLE_CHRONOS=true/ENABLE_CHRONOS=false/' .env

# Restart servicio
docker-compose restart forecaster_7d
```

### Si Sistema se Queda sin RAM

```bash
# Liberar memoria manualmente
docker system prune -a
systemctl restart docker

# Verificar procesos consumiendo RAM
ps aux --sort=-%mem | head -20

# Considerar reiniciar servidor si persiste
sudo reboot
```

### Si Modelo Corrompe

```bash
# Limpiar cache de Hugging Face
rm -rf ~/.cache/huggingface/hub/models--amazon--chronos-bolt-small

# Re-descargar en próxima ejecución
```

## Checklist de Deployment

Pre-deployment:
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Modelo descargado y cacheado
- [ ] RAM disponible > 1.5GB
- [ ] Test exitoso en desarrollo
- [ ] Logs configurados apropiadamente
- [ ] Alertas configuradas

Deployment:
- [ ] Variables de entorno configuradas
- [ ] Servicio reiniciado
- [ ] Primera ejecución monitoreada
- [ ] Logs verificados
- [ ] Reporte generado correctamente

Post-deployment (primera semana):
- [ ] Ejecución diaria exitosa
- [ ] RAM peak < 3GB
- [ ] Chronos peso en ensemble razonable (10-40%)
- [ ] Sin impacto en otros servicios
- [ ] Métricas registradas correctamente

Post-deployment (primer mes):
- [ ] Performance estable
- [ ] Consideración de expansión a otros servicios
- [ ] Optimización de hiperparámetros si necesario

## Soporte y Troubleshooting

### Logs Importantes

```bash
# Logs generales
/var/log/forecaster_7d.log

# Métricas de modelos
/path/to/logs/metrics.jsonl

# Docker logs
docker-compose logs forecaster_7d

# System logs
journalctl -u forecaster_7d.service
```

### Comandos Útiles de Diagnóstico

```bash
# Estado de memoria
free -h

# Procesos por RAM
ps aux --sort=-%mem | head

# Verificar carga del servidor
uptime

# Espacio en disco
df -h

# Verificar modelo descargado
ls -lh ~/.cache/huggingface/hub/ | grep chronos

# Test rápido de Chronos
python -c "from forex_core.forecasting import get_chronos_pipeline; get_chronos_pipeline(); print('OK')"
```

### Contacto

Para issues o preguntas durante deployment:
- Revisar [documentación técnica](./CHRONOS_INTEGRATION.md)
- Consultar logs del sistema
- Revisar [ejemplos de uso](../examples/README_CHRONOS.md)

## Conclusión

El deployment de Chronos es un proceso gradual que debe hacerse con monitoreo cuidadoso. La clave es:

1. **Empezar pequeño**: Solo forecaster_7d
2. **Monitorear intensivamente**: Primeras 2 semanas
3. **Expandir gradualmente**: Si métricas son buenas
4. **Optimizar**: Después de 1 mes de datos

Con esta estrategia, se minimiza el riesgo y se maximiza el aprendizaje del sistema.
