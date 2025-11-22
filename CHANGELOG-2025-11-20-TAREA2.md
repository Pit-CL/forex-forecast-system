# CHANGELOG - TAREA 2: Backtesting Retroactivo

**Fecha:** 2025-11-20
**Duración:** 60 minutos
**Status:** COMPLETADO

---

## Implementación

### Script Nuevo: backtest_historical.py

Walk-Forward Validation sobre datos históricos

- Carga modelos ElasticNet entrenados
- Usa MISMA función compute_features() que generate_real_forecasts.py
- Validación retroactiva últimos 90 días
- Métricas: MAE, RMSE, MAPE, Directional Accuracy
- Output: /backtest/metrics.json

---

## Resultados (Métricas Reales)

### 7D Horizon (29 samples)
- MAE: 21.69 CLP
- RMSE: 25.61 CLP
- MAPE: 2.27% (Excelente)
- Directional Accuracy: 72.4%

### 15D Horizon (23 samples)
- MAE: 15.68 CLP
- RMSE: 19.87 CLP
- MAPE: 1.65% (Excelente)
- Directional Accuracy: 87.0%

### 30D Horizon (12 samples)
- MAE: 17.24 CLP
- RMSE: 18.72 CLP
- MAPE: 1.83% (Excelente)
- Directional Accuracy: 100%

---

## Integración Cron

Modificado: scripts/auto_update_and_train.sh

Step 2e agregado (después de generate_real_forecasts.py):
- Ejecuta backtest_historical.py
- Non-blocking (no exit on failure)
- Logs a auto_update_YYYYMMDD.log

---

## API Verification

Endpoint: GET /api/performance

Retorna métricas REALES de backtesting:
- ElasticNet 7D:  MAPE 2.27%, DA 72.4%
- ElasticNet 15D: MAPE 1.65%, DA 87.0%
- ElasticNet 30D: MAPE 1.83%, DA 100%

---

## Problemas Resueltos

1. Predicciones absurdas (8x precio real)
   - Causa: Feature engineering incorrecto
   - Fix: Copiar compute_features() exacta

2. Métricas NaN
   - Causa: Valores futuros con NaN en CSV
   - Fix: Filtrar np.isnan() antes de append

---

## Comparación: Mock vs Real

| Horizon | MAPE Mock | MAPE Real | Mejora |
|---------|-----------|-----------|--------|
| 7D      | 5.16%     | 2.27%     | 56%    |
| 15D     | 6.33%     | 1.65%     | 74%    |
| 30D     | 7.70%     | 1.83%     | 76%    |

Conclusión: Modelos ElasticNet son MUCHO mejores de lo estimado

---

Desarrollado por: @senior-developer
Fecha: 2025-11-20 20:37-20:45
