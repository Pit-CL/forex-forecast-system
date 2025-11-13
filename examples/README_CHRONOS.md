# Ejemplos de Uso de Chronos

Este directorio contiene scripts de ejemplo para probar y usar la integración de Chronos-Bolt-Small.

## test_chronos_integration.py

Script completo de pruebas para validar la integración de Chronos.

### Requisitos

```bash
# Instalar dependencias
pip install -r requirements.txt

# Verificar que chronos-forecasting esté instalado
pip show chronos-forecasting
```

### Ejecución

```bash
# Desde el directorio raíz del proyecto
python examples/test_chronos_integration.py
```

### Tests Incluidos

1. **Standalone Forecast**: Prueba Chronos de forma aislada
   - Carga datos históricos USD/CLP
   - Genera pronóstico de 7 días
   - Valida estructura de ForecastPackage
   - Muestra métricas de validación

2. **Ensemble Integration**: Prueba Chronos integrado con otros modelos
   - Combina ARIMA, VAR y Chronos
   - Calcula pesos del ensemble
   - Compara métricas entre modelos
   - Genera pronóstico combinado

3. **Memory Cleanup**: Verifica gestión de memoria
   - Mide RAM antes de cargar modelo
   - Mide RAM después de cargar modelo
   - Libera modelo y mide RAM recuperada

### Salida Esperada

```
[INFO] Chronos-Bolt-Small Integration Test Suite
============================================================
[INFO] Available RAM: 2500MB
[INFO] Required RAM: 800MB

============================================================
TEST 1: Chronos Standalone Forecast
============================================================
[INFO] Loading historical USD/CLP data...
[INFO] Loaded 500 days of data
[INFO] Last price: 945.23 CLP

[INFO] Generating Chronos forecast (7 days)...
[INFO] Chronos inference completed in 3.45s
[INFO] Chronos pseudo-validation RMSE: 2.34

[INFO] ✓ Forecast generated successfully!
[INFO] Methodology: Chronos-Bolt-Small (pretrained transformer, context=180, samples=100)

[INFO] 7-Day Forecast:
------------------------------------------------------------
Day 1 (2025-11-14): 946.12 CLP (95% CI: [930.45, 961.79])
Day 2 (2025-11-15): 947.23 CLP (95% CI: [929.67, 964.79])
...

============================================================
TEST 2: Chronos in Ensemble with Other Models
============================================================
[INFO] Models enabled:
  - ARIMA: True
  - VAR: True
  - Random Forest: False
  - Chronos: True

[INFO] ✓ Ensemble forecast generated successfully!

[INFO] Ensemble Weights:
------------------------------------------------------------
  arima_garch    : 0.3500 (35.0%)
  var            : 0.3000 (30.0%)
  chronos        : 0.3500 (35.0%)

[INFO] ✓ Chronos contributed 35.0% to ensemble

============================================================
TEST 3: Memory Cleanup
============================================================
[INFO] Available RAM before loading: 2500MB
[INFO] Available RAM after loading: 1950MB
[INFO] Memory used by model: ~550MB
[INFO] Available RAM after release: 2480MB
[INFO] Memory freed: ~530MB

[INFO] ✓ Memory cleanup successful

============================================================
TEST SUMMARY
============================================================
Standalone Forecast      : ✓ PASSED
Ensemble Integration     : ✓ PASSED
Memory Cleanup           : ✓ PASSED

[INFO] 🎉 All tests passed!
```

## Uso Programático

### Ejemplo 1: Forecast Standalone

```python
from forex_core.forecasting import forecast_chronos
from forex_core.data.loader import load_data

# Cargar datos
bundle = load_data()
series = bundle.usdclp_series

# Generar forecast
forecast = forecast_chronos(
    series=series,
    steps=7,
    context_length=180,
    num_samples=100
)

# Usar resultados
for point in forecast.series:
    print(f"{point.date}: {point.mean:.2f} ± {point.std_dev:.2f}")
```

### Ejemplo 2: Forecast con Ensemble

```python
from forex_core.forecasting import ForecastEngine
from forex_core.config import get_settings
from forex_core.data.loader import load_data

# Configurar
settings = get_settings()
settings.enable_chronos = True

# Crear engine
engine = ForecastEngine(settings, horizon="daily", steps=7)

# Generar forecast
bundle = load_data()
forecast, artifacts = engine.forecast(bundle)

# Revisar pesos
print(f"Chronos weight: {artifacts.weights.get('chronos', 0):.2%}")
```

### Ejemplo 3: Control de Memoria

```python
from forex_core.forecasting import (
    forecast_chronos,
    release_chronos_pipeline
)

# Generar múltiples forecasts
for horizon in [7, 15, 30]:
    forecast = forecast_chronos(series, steps=horizon)
    # Procesar forecast...

# Liberar memoria al finalizar
release_chronos_pipeline()
```

## Troubleshooting

### Error: ImportError: cannot import name 'forecast_chronos'

**Solución**: Instalar dependencias de Chronos
```bash
pip install chronos-forecasting torch
```

### Error: MemoryError: Insufficient memory

**Solución 1**: Liberar RAM
```python
from forex_core.forecasting import release_chronos_pipeline
release_chronos_pipeline()
```

**Solución 2**: Deshabilitar Chronos temporalmente
```bash
# En .env
ENABLE_CHRONOS=false
```

### Warning: Chronos validation failed

**Causa**: Datos insuficientes para validación

**Solución**: Asegurar al menos 90 días de historia
```python
# Verificar longitud de serie
print(f"Serie length: {len(series)} days")
# Debe ser >= 60 para validación
```

### Inference muy lenta (>30s)

**Causa**: Primera carga del modelo o CPU lento

**Soluciones**:
1. Reducir muestras: `num_samples=50`
2. Reducir contexto: `context_length=90`
3. Esperar (segunda ejecución será más rápida)

## Performance Benchmarks

Tiempos típicos en AMD EPYC 2 vCPU, 4GB RAM:

| Operación | Primera Vez | Subsecuentes |
|-----------|-------------|--------------|
| Carga modelo | ~8-12s | ~0.5s (cache) |
| Forecast 7d | ~3-5s | ~3-5s |
| Forecast 30d | ~5-8s | ~5-8s |
| Validación | +2-3s | +2-3s |

Uso de memoria:
- Modelo en RAM: ~400-600MB
- Inference peak: ~800-1000MB
- Post-cleanup: ~100-200MB

## Referencias

- [Documentación Chronos Integration](../docs/CHRONOS_INTEGRATION.md)
- [Chronos Paper](https://arxiv.org/abs/2403.07815)
- [Chronos GitHub](https://github.com/amazon-science/chronos-forecasting)
