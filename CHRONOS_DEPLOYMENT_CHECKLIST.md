# Checklist de Deployment: Chronos-Bolt-Small

Usa este checklist para verificar cada paso del deployment de Chronos en producción.

---

## Pre-Deployment

### Verificación de Código

- [ ] Todos los archivos nuevos creados:
  - [ ] `src/forex_core/forecasting/chronos_model.py`
  - [ ] `docs/CHRONOS_INTEGRATION.md`
  - [ ] `docs/CHRONOS_PRODUCTION_DEPLOYMENT.md`
  - [ ] `docs/CHRONOS_IMPLEMENTATION_SUMMARY.md`
  - [ ] `examples/test_chronos_integration.py`
  - [ ] `examples/README_CHRONOS.md`

- [ ] Modificaciones correctas en:
  - [ ] `src/forex_core/forecasting/models.py` (método `_run_chronos`)
  - [ ] `src/forex_core/forecasting/__init__.py` (exports de Chronos)
  - [ ] `src/forex_core/config/base.py` (flags `enable_chronos`)
  - [ ] `requirements.txt` (torch, chronos-forecasting, psutil)

### Testing Local

- [ ] **Instalar dependencias**
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **Verificar instalación**
  ```bash
  python -c "import chronos; import torch; import psutil; print('OK')"
  ```

- [ ] **Ejecutar test suite**
  ```bash
  python examples/test_chronos_integration.py
  ```
  Resultado esperado: `✓ All tests passed!`

- [ ] **Revisar logs de test**
  - [ ] Chronos cargó correctamente
  - [ ] Forecast generado exitosamente
  - [ ] Ensemble incluyó Chronos
  - [ ] Memoria liberada correctamente

### Revisión de Documentación

- [ ] Leer [CHRONOS_INTEGRATION.md](docs/CHRONOS_INTEGRATION.md)
- [ ] Leer [CHRONOS_PRODUCTION_DEPLOYMENT.md](docs/CHRONOS_PRODUCTION_DEPLOYMENT.md)
- [ ] Familiarizarse con [ejemplos](examples/README_CHRONOS.md)
- [ ] Entender troubleshooting común

---

## Deployment en Servidor de Desarrollo

### Preparación del Servidor

- [ ] **SSH al servidor**
  ```bash
  ssh user@dev-server
  ```

- [ ] **Verificar recursos**
  ```bash
  free -h  # RAM disponible > 1.5GB
  df -h    # Espacio > 1GB
  ```

- [ ] **Pull código actualizado**
  ```bash
  cd /path/to/forex-forecast-system
  git pull origin develop
  ```

### Instalación de Dependencias

- [ ] **Activar entorno virtual**
  ```bash
  source venv/bin/activate
  ```

- [ ] **Actualizar pip**
  ```bash
  pip install --upgrade pip
  ```

- [ ] **Instalar dependencias**
  ```bash
  pip install -r requirements.txt
  ```
  ⏱️ Tiempo estimado: 5-10 minutos

- [ ] **Pre-descargar modelo**
  ```bash
  python -c "from chronos import ChronosPipeline; ChronosPipeline.from_pretrained('amazon/chronos-bolt-small')"
  ```
  ⏱️ Tiempo estimado: 2-5 minutos

- [ ] **Verificar instalación**
  ```bash
  python -c "from forex_core.forecasting import get_chronos_pipeline; get_chronos_pipeline(); print('✓ OK')"
  ```

### Configuración

- [ ] **Crear archivo .env para forecaster_7d**
  ```bash
  cd src/services/forecaster_7d
  cat > .env.chronos << EOF
  ENABLE_CHRONOS=true
  CHRONOS_CONTEXT_LENGTH=180
  CHRONOS_NUM_SAMPLES=100
  EOF
  ```

- [ ] **Backup configuración actual**
  ```bash
  cp .env .env.backup.$(date +%Y%m%d)
  ```

### Test en Desarrollo

- [ ] **Ejecutar forecaster manualmente**
  ```bash
  cd /path/to/forex-forecast-system
  export ENABLE_CHRONOS=true
  python -m services.forecaster_7d.pipeline
  ```

- [ ] **Verificar logs** (durante ejecución)
  ```bash
  tail -f logs/forecaster_7d.log
  ```

- [ ] **Buscar líneas clave en logs**:
  - [ ] "Loading Chronos pipeline"
  - [ ] "Chronos inference completed in X.XXs"
  - [ ] "Chronos pseudo-validation RMSE"
  - [ ] "Ensemble weights: {..., 'chronos': X.XX}"

- [ ] **Verificar salida**:
  - [ ] Reporte generado correctamente
  - [ ] Chronos mencionado en metodología
  - [ ] No errores en logs

- [ ] **Monitorear recursos**:
  - [ ] Peak RAM < 3GB
  - [ ] Tiempo total < baseline + 10s
  - [ ] CPU normal post-ejecución

---

## Deployment en Producción

### Pre-Deployment en Producción

- [ ] **Tests en desarrollo exitosos** (mínimo 2 ejecuciones)
- [ ] **Métricas revisadas y aceptables**
- [ ] **Plan de rollback documentado**
- [ ] **Ventana de mantenimiento coordinada** (opcional)

### Backup

- [ ] **Backup de código actual**
  ```bash
  cd /path/to/forex-forecast-system
  git tag backup-pre-chronos-$(date +%Y%m%d)
  git push origin backup-pre-chronos-$(date +%Y%m%d)
  ```

- [ ] **Backup de configuración**
  ```bash
  cp .env .env.backup.$(date +%Y%m%d)
  ```

- [ ] **Backup de base de datos** (si aplica)

### Deployment

- [ ] **SSH al servidor de producción**
  ```bash
  ssh user@prod-server
  ```

- [ ] **Pull código**
  ```bash
  cd /path/to/forex-forecast-system
  git pull origin main  # o develop, según tu estrategia
  ```

- [ ] **Instalar dependencias**
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

- [ ] **Pre-descargar modelo**
  ```bash
  python -c "from chronos import ChronosPipeline; ChronosPipeline.from_pretrained('amazon/chronos-bolt-small')"
  ```

- [ ] **Configurar forecaster_7d**
  ```bash
  cd src/services/forecaster_7d
  echo "ENABLE_CHRONOS=true" >> .env
  echo "CHRONOS_CONTEXT_LENGTH=180" >> .env
  echo "CHRONOS_NUM_SAMPLES=100" >> .env
  ```

- [ ] **Rebuild Docker images** (si aplica)
  ```bash
  docker-compose build forecaster_7d
  ```

- [ ] **Test manual antes de cron**
  ```bash
  # Simular ejecución de cron
  docker-compose run --rm forecaster_7d python -m services.forecaster_7d.pipeline
  ```

- [ ] **Verificar test manual exitoso**

### Activación del Servicio

- [ ] **Restart servicio**
  ```bash
  docker-compose restart forecaster_7d
  # O
  systemctl restart forecaster_7d.service
  ```

- [ ] **Verificar servicio corriendo**
  ```bash
  docker-compose ps
  # O
  systemctl status forecaster_7d.service
  ```

- [ ] **Verificar logs en tiempo real**
  ```bash
  docker-compose logs -f forecaster_7d
  ```

---

## Post-Deployment (Primeras 24 Horas)

### Monitoreo Inmediato

- [ ] **Esperar primera ejecución automática** (próximo lunes)

- [ ] **Durante ejecución, monitorear**:
  ```bash
  # Terminal 1: Logs
  docker-compose logs -f forecaster_7d

  # Terminal 2: RAM
  watch -n 1 'free -h'

  # Terminal 3: CPU
  htop
  ```

- [ ] **Verificar ejecución exitosa**:
  - [ ] Logs sin errores
  - [ ] Reporte generado
  - [ ] Email enviado (si configurado)

### Validación Post-Ejecución

- [ ] **Revisar reporte generado**
  - [ ] PDF/HTML existe
  - [ ] Chronos mencionado en metodología
  - [ ] Gráficos correctos
  - [ ] Intervalos de confianza razonables

- [ ] **Revisar métricas**
  ```bash
  tail -5 logs/metrics.jsonl | jq '.'
  ```

  Verificar:
  - [ ] Entrada de Chronos presente
  - [ ] RMSE y MAPE registrados
  - [ ] Peso en ensemble razonable (10-40%)

- [ ] **Verificar recursos del sistema**
  - [ ] RAM volvió a nivel normal
  - [ ] CPU normal
  - [ ] Otros servicios no afectados

### Documentación

- [ ] **Registrar resultados** en log interno:
  - Fecha y hora de ejecución
  - Peso de Chronos en ensemble
  - RMSE y MAPE de Chronos
  - Peak RAM usage
  - Tiempo de ejecución total
  - Observaciones

---

## Post-Deployment (Primera Semana)

### Monitoreo Diario

- [ ] **Lunes**: Revisar logs de ejecución semanal
- [ ] **Martes-Viernes**: Verificar que no hay efectos secundarios
- [ ] **Sábado**: No aplica (forecaster_7d no corre)
- [ ] **Domingo**: Preparación para próxima ejecución

### Checklist Semanal

- [ ] **Ejecución exitosa** (sin errores)
- [ ] **Peak RAM** < 3GB
- [ ] **Tiempo ejecución** aceptable (< baseline + 10s)
- [ ] **Peso Chronos** razonable (10-40%)
- [ ] **RMSE Chronos** competitivo con ARIMA/VAR
- [ ] **Otros servicios** no afectados

### Revisión de Métricas

- [ ] **Extraer métricas semanales**
  ```bash
  grep chronos logs/metrics.jsonl | tail -4 | jq -s '.'
  ```

- [ ] **Comparar con baseline** (sin Chronos)

- [ ] **Documentar observaciones**

---

## Post-Deployment (Primer Mes)

### Revisión Mensual

- [ ] **Recolectar métricas de 4 semanas**
- [ ] **Calcular promedios**:
  - [ ] RMSE promedio de Chronos
  - [ ] Peso promedio en ensemble
  - [ ] Peak RAM promedio
  - [ ] Tiempo ejecución promedio

- [ ] **Comparar con otros modelos**:
  - [ ] Chronos vs ARIMA
  - [ ] Chronos vs VAR
  - [ ] Ensemble con vs sin Chronos

### Decisión de Expansión

Si métricas son satisfactorias:

- [ ] **Habilitar en forecaster_15d**
  ```bash
  cd src/services/forecaster_15d
  echo "ENABLE_CHRONOS=true" >> .env
  docker-compose restart forecaster_15d
  ```

- [ ] **Repetir proceso de monitoreo** para forecaster_15d

Si métricas NO son satisfactorias:

- [ ] **Analizar causas**
- [ ] **Ajustar hiperparámetros**:
  - Reducir `num_samples` a 50-75
  - Ajustar `context_length`
  - Modificar `temperature`
- [ ] **Re-test con nuevos parámetros**

---

## Rollback (Si Necesario)

### Indicadores para Rollback

Ejecutar rollback si:
- [ ] Chronos falla > 2 veces consecutivas
- [ ] Peak RAM > 3.5GB consistentemente
- [ ] Tiempo ejecución aumenta > 20s
- [ ] Sistema se queda sin memoria
- [ ] Otros servicios afectados

### Procedimiento de Rollback

- [ ] **Deshabilitar Chronos**
  ```bash
  cd src/services/forecaster_7d
  sed -i 's/ENABLE_CHRONOS=true/ENABLE_CHRONOS=false/' .env
  ```

- [ ] **Restart servicio**
  ```bash
  docker-compose restart forecaster_7d
  ```

- [ ] **Verificar funcionamiento sin Chronos**

- [ ] **Analizar causa del problema**

- [ ] **Documentar incidente**

- [ ] **Planear re-intento** (después de fix)

---

## Expansión Gradual

### Forecaster 15d

Después de 2-4 semanas exitosas en forecaster_7d:

- [ ] Aplicar mismo proceso que forecaster_7d
- [ ] Monitorear 2 semanas
- [ ] Documentar resultados

### Forecaster 30d

Después de 2 semanas exitosas en forecaster_15d:

- [ ] Aplicar mismo proceso
- [ ] Ajustar `context_length=90` (3 meses)
- [ ] Monitorear 2 semanas
- [ ] Documentar resultados

### Forecaster 90d (Opcional)

Solo si Chronos demuestra excelente performance en otros horizontes:

- [ ] Evaluar cuidadosamente
- [ ] Ajustar `context_length=365` (1 año)
- [ ] Monitorear muy de cerca
- [ ] Considerar deshabilitar si RMSE alto

---

## Optimización Continua

### Trimestral

- [ ] **Revisar métricas agregadas**
- [ ] **Ajustar hiperparámetros** si necesario
- [ ] **Evaluar nuevas versiones** de Chronos
- [ ] **Considerar fine-tuning** (futuro)

### Anual

- [ ] **Revisión completa de performance**
- [ ] **Evaluar alternativas**:
  - Chronos-Bolt-Base (más grande)
  - GPU inference
  - Fine-tuning en datos USD/CLP
- [ ] **Actualizar documentación**

---

## Contactos y Recursos

### En caso de problemas

1. **Revisar logs**:
   - `/var/log/forecaster_7d.log`
   - `logs/metrics.jsonl`

2. **Consultar documentación**:
   - [CHRONOS_INTEGRATION.md](docs/CHRONOS_INTEGRATION.md)
   - [CHRONOS_PRODUCTION_DEPLOYMENT.md](docs/CHRONOS_PRODUCTION_DEPLOYMENT.md)

3. **Ejecutar diagnósticos**:
   ```bash
   python examples/test_chronos_integration.py
   ```

4. **Rollback si crítico** (ver sección Rollback arriba)

### Recursos Útiles

- **Paper**: https://arxiv.org/abs/2403.07815
- **GitHub**: https://github.com/amazon-science/chronos-forecasting
- **Hugging Face**: https://huggingface.co/amazon/chronos-bolt-small
- **PyTorch Docs**: https://pytorch.org/docs/stable/index.html

---

## Notas Finales

- ✅ Este checklist cubre deployment completo de Chronos
- ✅ Seguir secuencialmente para minimizar riesgos
- ✅ Documentar cada paso y observaciones
- ✅ No apresurarse - monitoreo es clave
- ✅ Rollback es siempre una opción válida

**Última actualización**: 2025-11-13
**Versión**: 1.0.0
