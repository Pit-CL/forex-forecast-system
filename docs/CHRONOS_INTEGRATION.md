# Integración de Chronos-Bolt-Small en Forex Forecast System

## Resumen

Se ha integrado **Chronos-Bolt-Small**, un modelo transformer preentrenado para forecasting de series temporales, en el sistema de pronóstico USD/CLP. Chronos es un foundation model desarrollado por Amazon que puede pronosticar series temporales sin entrenamiento adicional (zero-shot forecasting).

## ¿Qué es Chronos?

Chronos es una familia de modelos de deep learning pretrained para forecasting de series temporales. Utiliza una arquitectura transformer y ha sido entrenado en un conjunto masivo de datos de series temporales diversas, lo que le permite generalizar a nuevos dominios sin fine-tuning.

**Referencia**: Ansari et al. (2024). "Chronos: Learning the Language of Time Series" - https://arxiv.org/abs/2403.07815

**Variante integrada**: Chronos-Bolt-Small (~100M parámetros)
- Suficientemente pequeño para 4GB RAM
- Balance óptimo entre precisión y velocidad
- Compatible con CPU inference

## Características de la Integración

### 1. **Zero-Shot Forecasting**
- No requiere entrenamiento ni fine-tuning
- Funciona inmediatamente con datos históricos USD/CLP
- Aprovecha el conocimiento preentrenado de miles de series temporales

### 2. **Pronósticos Probabilísticos**
- Genera 100 muestras por predicción (configurable)
- Calcula intervalos de confianza 80% y 95%
- Captura la incertidumbre de forma natural

### 3. **Context-Length Adaptativo**
- 7d/15d forecast: 180 días de historia (6 meses)
- 30d forecast: 90 días de historia (3 meses)
- 90d forecast: 365 días de historia (1 año)

### 4. **Memory-Efficient**
- Patrón singleton para cargar el modelo una sola vez
- Verificación de RAM disponible antes de ejecutar
- Liberación manual de memoria disponible
- Estimado de uso: ~400-600MB

### 5. **Pseudo-Validación**
- Valida el modelo usando los últimos 30 días de historia
- Calcula RMSE y MAPE pseudo out-of-sample
- Permite comparación justa con modelos estadísticos

### 6. **Integración con Ensemble**
- Compatible con ForecastPackage estándar
- Se integra automáticamente en el ensemble ponderado
- Peso determinado por pseudo-validation RMSE

## Instalación

### 1. Instalar Dependencias

```bash
# Desde el directorio raíz del proyecto
pip install -r requirements.txt
```

Esto instalará:
- `torch>=2.0.0` - PyTorch para deep learning
- `chronos-forecasting>=1.2.0` - Librería oficial de Chronos
- `psutil>=5.9` - Para monitoreo de memoria

### 2. Verificar Instalación

```python
from forex_core.forecasting import forecast_chronos, get_chronos_pipeline

# Intentar cargar el pipeline (descargará el modelo la primera vez)
try:
    pipeline = get_chronos_pipeline()
    print("✓ Chronos instalado correctamente")
except Exception as e:
    print(f"✗ Error: {e}")
```

**Nota**: La primera ejecución descargará el modelo (~400MB) desde Hugging Face Hub. Requiere conexión a internet.

## Configuración

### Variables de Entorno

Agregar al archivo `.env`:

```bash
# Habilitar/deshabilitar Chronos
ENABLE_CHRONOS=true

# Configuración de Chronos (opcional)
CHRONOS_CONTEXT_LENGTH=180      # Días de historia a usar
CHRONOS_NUM_SAMPLES=100         # Número de muestras probabilísticas
```

### Configuración por Servicio

Cada servicio de forecasting puede habilitar Chronos individualmente:

**Ejemplo: forecaster_7d/config.py**
```python
from forex_core.config import Settings

class Forecaster7dSettings(Settings):
    enable_chronos: bool = True  # Habilitar Chronos para 7d
```

## Uso

### 1. Uso Directo (sin ensemble)

```python
import pandas as pd
from forex_core.forecasting import forecast_chronos

# Cargar serie temporal
series = pd.Series([950, 945, 955, ...], index=pd.date_range(...))

# Generar forecast
forecast = forecast_chronos(
    series=series,
    steps=7,                    # 7 días hacia adelante
    context_length=180,         # Usar 6 meses de historia
    num_samples=100,            # 100 muestras probabilísticas
    validate=True               # Ejecutar pseudo-validación
)

# Inspeccionar resultados
print(f"Pronóstico día 7: {forecast.series[-1].mean:.2f}")
print(f"Intervalo 95%: [{forecast.series[-1].ci95_low:.2f}, {forecast.series[-1].ci95_high:.2f}]")
print(f"Metodología: {forecast.methodology}")
print(f"Pseudo-RMSE: {forecast.error_metrics['pseudo_RMSE']:.4f}")
```

### 2. Uso con ForecastEngine (Ensemble)

```python
from forex_core.forecasting import ForecastEngine
from forex_core.config import get_settings
from forex_core.data.loader import load_data

# Configurar con Chronos habilitado
settings = get_settings()
settings.enable_chronos = True

# Crear engine
engine = ForecastEngine(
    config=settings,
    horizon="daily",
    steps=7
)

# Cargar datos
bundle = load_data()

# Generar ensemble forecast (incluye Chronos)
forecast, artifacts = engine.forecast(bundle)

# Inspeccionar pesos del ensemble
print(f"Pesos del ensemble: {artifacts.weights}")
# Ejemplo: {'arima_garch': 0.35, 'var': 0.30, 'random_forest': 0.20, 'chronos': 0.15}
```

### 3. Liberar Memoria

```python
from forex_core.forecasting import release_chronos_pipeline

# Después de generar forecasts
release_chronos_pipeline()  # Libera ~400-600MB RAM
```

## Consideraciones de Producción

### 1. **Memoria RAM**
- Requiere al menos 800MB de RAM disponible
- Recomendado: 1.5GB+ de RAM libre
- El sistema verifica memoria antes de ejecutar
- Si RAM insuficiente, Chronos se salta y ensemble usa otros modelos

### 2. **Tiempo de Inferencia**
- CPU inference: ~2-10 segundos por forecast
- GPU inference (opcional): ~0.5-2 segundos
- Primera ejecución más lenta (carga del modelo)
- Ejecuciones subsecuentes usan modelo en cache

### 3. **Prioridad de Habilitación**

**Recomendación**: Habilitar en orden de menor a mayor riesgo

1. **forecaster_7d** (recomendado primero)
   - Corre semanalmente los lunes
   - Menor frecuencia = menos carga
   - Horizonte corto = mejor para Chronos

2. **forecaster_15d**
   - Similar a 7d, buen candidato

3. **forecaster_30d**
   - Horizonte medio, Chronos puede agregar valor

4. **forecaster_90d**
   - Horizonte largo, Chronos menos confiable
   - Evaluar performance antes de habilitar

### 4. **Manejo de Errores**

El sistema es robusto ante fallos de Chronos:
- Si Chronos falla, se registra un warning
- El ensemble continúa con los demás modelos
- No hay interrupción del servicio

```python
# Ejemplo de log si Chronos falla
WARNING: Chronos failed: Insufficient memory for Chronos: 500MB available, 800MB required
INFO: Ensemble weights: {'arima_garch': 0.45, 'var': 0.35, 'random_forest': 0.20}
```

### 5. **Monitoreo**

Métricas a monitorear:
- **Pseudo-RMSE**: Precisión de validación
- **Peso en Ensemble**: Contribución al pronóstico final
- **Tiempo de Inferencia**: Performance
- **Uso de Memoria**: Picos de RAM durante ejecución

Ejemplo de logs:
```
INFO: Running Chronos model (available RAM: 2500MB)
INFO: Chronos forecast: 7 steps, context=180, samples=100
DEBUG: Generating Chronos forecast samples...
INFO: Chronos inference completed in 3.45s
INFO: Chronos pseudo-validation RMSE: 2.34
INFO: Chronos forecast complete: mean=945.23, std=8.12
```

## Ventajas de Chronos

1. **Zero-Shot Learning**: No requiere entrenamiento, funciona inmediatamente
2. **Captura Patrones Complejos**: Transformer aprende dependencias de largo plazo
3. **Incertidumbre Calibrada**: Intervalos de confianza realistas
4. **Robustez**: Pretrenado en miles de series, menos overfitting
5. **Complementariedad**: Aporta perspectiva diferente a modelos estadísticos

## Limitaciones

1. **Recursos Computacionales**: Requiere más RAM y tiempo que ARIMA/VAR
2. **Interpretabilidad**: Modelo black-box, difícil explicar decisiones
3. **Horizonte**: Mejor en corto plazo (7-30d) que largo plazo (90d+)
4. **Dependencia Externa**: Requiere librerías de deep learning (torch)
5. **Primera Descarga**: Necesita internet para descargar modelo inicial

## Troubleshooting

### Error: "chronos-forecasting package not installed"

```bash
pip install chronos-forecasting torch
```

### Error: "Insufficient memory for Chronos"

Opciones:
1. Aumentar RAM disponible (cerrar otras apps)
2. Deshabilitar Chronos: `ENABLE_CHRONOS=false` en `.env`
3. Usar servidor con más RAM

### Warning: "Chronos validation failed"

- No crítico, Chronos sigue funcionando
- Revisa que la serie tenga suficiente historia (>60 días)
- Puede ocurrir en series con muchos valores faltantes

### Inference muy lenta (>30s)

- Normal en CPU la primera vez (carga del modelo)
- Si persiste, considera:
  - Reducir `CHRONOS_NUM_SAMPLES` a 50
  - Reducir `CHRONOS_CONTEXT_LENGTH` a 90
  - Usar GPU si disponible

## Próximos Pasos

### Fase 1: Validación (Actual)
- ✅ Implementar integración básica
- ✅ Agregar pseudo-validación
- ⏳ Habilitar en forecaster_7d
- ⏳ Monitorear performance 2-4 semanas

### Fase 2: Expansión
- ⏳ Evaluar resultados en 7d
- ⏳ Habilitar en forecaster_15d
- ⏳ Optimizar hiperparámetros (context_length, num_samples)

### Fase 3: Optimización
- ⏳ Considerar fine-tuning en datos USD/CLP
- ⏳ Evaluar Chronos-Bolt-Base (si más RAM disponible)
- ⏳ GPU inference si disponible

## Referencias

- [Chronos Paper (arXiv)](https://arxiv.org/abs/2403.07815)
- [Chronos GitHub](https://github.com/amazon-science/chronos-forecasting)
- [Hugging Face Model Card](https://huggingface.co/amazon/chronos-bolt-small)
- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)

## Contacto

Para preguntas o issues sobre la integración de Chronos:
- Revisar logs en `/logs/metrics.jsonl`
- Consultar documentación técnica en código fuente
- Abrir issue en repositorio del proyecto
