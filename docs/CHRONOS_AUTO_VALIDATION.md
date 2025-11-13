# Chronos Auto-Validation System

Sistema de validación automática para determinar cuándo es seguro habilitar el modelo foundation Chronos en producción.

## Descripción General

El sistema evalúa múltiples criterios para garantizar que:
1. El sistema de tracking está acumulando suficiente data
2. La detección de drift funciona correctamente
3. El sistema es estable (sin errores críticos)
4. Hay suficiente tiempo de operación para establecer baselines
5. Existen métricas de performance para comparar

## Criterios de Validación

### 1. **Prediction Tracking Data** (CRÍTICO)
- **Requisito**: Mínimo 50 predictions por horizon (7d, 15d, 30d, 90d)
- **Por qué**: Necesitamos baseline de predictions actuales antes de agregar Chronos
- **Score**: `(predictions_count / 50) * 100`

### 2. **Operation Time** (CRÍTICO)
- **Requisito**: Mínimo 7 días de operación
- **Por qué**: Necesitamos ver el sistema en diferentes condiciones de mercado
- **Score**: `(days_operating / 7) * 100`

### 3. **Drift Detection Functionality**
- **Requisito**: Sistema generando predictions recientes (últimos 7 días)
- **Por qué**: Confirma que drift detection está corriendo
- **Score**: 100 si hay predictions recientes, 30 si no

### 4. **System Stability**
- **Requisito**: Log de métricas < 50MB, sin errores masivos
- **Por qué**: Chronos es memory-intensive, necesitamos sistema estable
- **Score**: 100 si estable, 40 si log grande, 70 si no se puede verificar

### 5. **Performance Baseline**
- **Requisito**: Mínimo 10 predictions con actuals por horizon
- **Por qué**: Necesitamos baseline para comparar si Chronos mejora
- **Score**: `(predictions_with_actuals / 10) * 100`

## Niveles de Readiness

### NOT_READY (Score < 60 o critical check failed)
- **Acción**: NO habilitar Chronos
- **Recomendación**: Esperar más tiempo, resolver issues críticos

### CAUTIOUS (Score 60-74)
- **Acción**: Puede habilitar con monitoreo cercano
- **Recomendación**: Habilitar solo en 7d, monitorear closely

### READY (Score 75-89)
- **Acción**: Seguro habilitar con monitoreo estándar
- **Recomendación**: Habilitar en todos los horizontes

### OPTIMAL (Score ≥ 90)
- **Acción**: Condiciones ideales para habilitar
- **Recomendación**: Full rollout sin restricciones

## Uso

### 1. Check Manual

```bash
# Desde local
python scripts/check_chronos_readiness.py

# Desde Docker
docker exec usdclp-forecaster-7d python /app/scripts/check_chronos_readiness.py

# Con parámetros personalizados
python scripts/check_chronos_readiness.py \
  --min-predictions 100 \
  --min-days 14

# Output JSON para scripts
python scripts/check_chronos_readiness.py --json
```

### 2. Auto-Enable (Requiere Aprobación)

```bash
# Dry run (muestra qué haría sin cambiar nada)
python scripts/check_chronos_readiness.py auto-enable --dry-run

# Habilitar automáticamente si está ready
python scripts/check_chronos_readiness.py auto-enable

# Especificar archivo de config
python scripts/check_chronos_readiness.py auto-enable \
  --config-file /app/.env
```

### 3. Check Diario Automático

El script `daily_readiness_check.sh` puede configurarse en cron:

```bash
# Agregar a crontab (ejecuta diario a las 9 AM)
0 9 * * * /app/scripts/daily_readiness_check.sh >> /app/logs/readiness_checks.log 2>&1
```

El script:
- Ejecuta el check de readiness
- Guarda resultado en `data/chronos_readiness_status.txt`
- Logea recomendación si está READY
- **NO habilita automáticamente** (requiere acción manual)

### 4. Integración con Monitoring

Puedes crear alertas basadas en el archivo de estado:

```bash
# Verificar status actual
cat data/chronos_readiness_status.txt
# Output: READY|2025-11-13T09:00:00-03:00

# En script de monitoring
if grep -q "^READY" data/chronos_readiness_status.txt; then
    echo "Sistema listo para Chronos!"
    # Enviar notificación, crear ticket, etc.
fi
```

## Output Ejemplo

```
======================================================================
CHRONOS READINESS ASSESSMENT
======================================================================

Overall Level: READY
Score: 82.0/100
Timestamp: 2025-11-20 09:00:00

======================================================================
CHECK RESULTS
======================================================================

✓ Prediction Tracking Data [CRITICAL]
   Score: 90/100
   Found 450 total predictions. Min per horizon: 90 (need 50)

✓ Operation Time [CRITICAL]
   Score: 100/100
   System operating for 14 days (need 7)

✓ Drift Detection
   Score: 100/100
   System active: 98 predictions in last 7 days. Drift detection operational.

✓ System Stability
   Score: 100/100
   Metrics log size normal (2.3MB)

✗ Performance Baseline
   Score: 20/100
   Baseline data: 450 predictions with actuals. Min per horizon: 2

======================================================================
RECOMMENDATION
======================================================================

✓ READY: System meets requirements for Chronos enablement.
Enable with standard monitoring.
Consider starting with 7d horizon only for gradual rollout.
```

## Integración con CI/CD

### GitHub Actions Example

```yaml
name: Check Chronos Readiness

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
  workflow_dispatch:

jobs:
  check-readiness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check Chronos Readiness
        run: |
          python scripts/check_chronos_readiness.py --json > readiness.json

      - name: Parse Results
        id: readiness
        run: |
          LEVEL=$(jq -r '.level' readiness.json)
          SCORE=$(jq -r '.score' readiness.json)
          echo "level=$LEVEL" >> $GITHUB_OUTPUT
          echo "score=$SCORE" >> $GITHUB_OUTPUT

      - name: Create Issue if Ready
        if: steps.readiness.outputs.level == 'ready'
        uses: actions/create-issue@v2
        with:
          title: "System Ready for Chronos Enablement"
          body: |
            Automated readiness check indicates system is READY for Chronos.

            **Score**: ${{ steps.readiness.outputs.score }}/100
            **Level**: ${{ steps.readiness.outputs.level }}

            Review full report and approve enablement.
```

## Cronograma Recomendado

### Semana 1-2: Acumulación de Data
- ✅ Prediction tracking activo
- ✅ Drift detection corriendo
- ❌ Chronos deshabilitado
- **Check diario**: Monitorear progreso de criterios

### Semana 2-3: Validación
- Verificar que todos los checks pasan
- Revisar métricas de baseline
- Confirmar estabilidad del sistema

### Semana 3+: Habilitación Gradual
1. **Día 1**: Habilitar solo en `forecaster-7d`
2. **Día 3**: Si 7d estable, habilitar en `forecaster-15d`
3. **Día 7**: Si todo bien, habilitar en `forecaster-30d` y `forecaster-90d`
4. **Día 14**: Full rollout completo

## Monitoreo Post-Habilitación

Después de habilitar Chronos, monitorear:

1. **RAM Usage**: Debe mantenerse < 3.5GB
2. **Execution Time**: Puede aumentar 10-30s
3. **Forecast Quality**: Comparar métricas con baseline
4. **Error Rate**: No debe aumentar significativamente

## Rollback Plan

Si Chronos causa problemas:

```bash
# 1. Deshabilitar Chronos
sed -i 's/ENABLE_CHRONOS=true/ENABLE_CHRONOS=false/' .env

# 2. Restart services
docker compose restart

# 3. Verificar rollback
docker logs usdclp-forecaster-7d | grep "Chronos"
# Should NOT see Chronos loading messages
```

## FAQ

**Q: ¿Por qué 50 predictions mínimo?**
A: 50 predictions por horizon nos da ~1-2 semanas de data (7d corre diario, otros menos frecuente). Suficiente para establecer baseline pero no demasiado tiempo de espera.

**Q: ¿Puedo override los criterios?**
A: Sí, usa flags en el script: `--min-predictions 30 --min-days 5`. Pero no recomendado para producción.

**Q: ¿El auto-enable es seguro?**
A: El auto-enable solo actualiza .env si **todos** los criterios críticos pasan. Aún así, revisar logs antes de usar en prod.

**Q: ¿Qué pasa si el check falla?**
A: El script retorna exit code != 0, lo puedes usar en CI/CD. No hace cambios si no está ready.

**Q: ¿Cuánto tarda en estar READY típicamente?**
A: ~7-14 días dependiendo de frecuencia de forecasts y cuándo empiecen a llegar actuals para baseline.

## Referencias

- [Chronos Integration Guide](./CHRONOS_INTEGRATION.md)
- [Prediction Tracking Docs](./prediction-tracking.md)
- [Drift Detection README](./DRIFT_DETECTION_README.md)
