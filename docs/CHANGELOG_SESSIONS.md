# Sesión 2025-11-22: Integración Diferencial de Tasas

## Problemas Resueltos
1. **Entrenamiento 6AM falló**: Timeout mindicador.cl (UF)
   - Fix: collect_data.py línea 97 - ya no hardcodea columnas

2. **Nueva variable exógena**: Diferencial tasas Chile-USA
   - Fed Rate (DFF): 3.88% diario
   - Chile Rate (IRSTCI01CLM156N): 4.75% mensual
   - Diferencial actual: +0.87%

## Archivos Modificados
- scripts/collect_data.py: +40 líneas sección FRED
- data/raw/fred_interest_rates.csv: 5,803 filas desde 2010
- CHANGELOG.md: v1.0.2

## Estado
- Datos FRED: ✅ Colectándose
- Pipeline: ✅ Funcionando
- Próximo: Integrar en feature engineering

## Integración Completada - 13:56 UTC-3

### Cambios en Scripts de Entrenamiento
1. **retrain_elasticnet.py**: 
   - Agregado FRED_FILE constant
   - Merge de rate_differential después de cargar datos
   - Backup: retrain_elasticnet.py.bak_20251122

2. **train_models_v2.py** (LightGBM):
   - Agregado merge de FRED data
   - Backup: train_models_v2.py.bak_20251122

### Resultados MAPE ElasticNet
| Horizonte | Antes | Después | Mejora |
|-----------|-------|---------|--------|
| 7D  | 2.61% | 2.46% | -5.7% |
| 15D | 2.61% | 2.54% | -2.7% |
| 30D | 3.2%  | 3.13% | -2.2% |
| 90D | 6.5%  | 6.33% | -2.6% |

### Pipeline
- auto_update_and_train.sh: ✅ Funciona
- API: ✅ Healthy
- Pronósticos: ✅ Generándose con ElasticNet

### Datos FRED
- rate_differential rango: [-0.25, 8.42]
- Chile actual: 4.75%
- USA actual: 3.88%
- Diferencial actual: +0.87%

## Fix Adicional - 13:58 UTC-3

### Problema Detectado
- El cron usa  (LightGBM)
- Solo había modificado 

### Solución
- Agregado merge FRED a 
- Backup: train_models_v3_optimized.py.bak_20251122

### Pipeline Completo Verificado
| Paso | Script | FRED |
|------|--------|------|
| 1. Colectar datos | collect_data.py | ✅ |
| 2a. LightGBM | train_models_v3_optimized.py | ✅ |
| 2b. ElasticNet | retrain_elasticnet.py | ✅ |
| 2c. Generar JSON | generate_real_forecasts.py | ✅ |
| 3. Restart API | docker compose restart | ✅ |

### Cron Activo
-  - Todos los días 6 AM Chile
- Dashboard se actualiza automáticamente (lee de API)
