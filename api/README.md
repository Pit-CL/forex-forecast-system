# Forex Forecast System API

Backend API para el dashboard de forecasts USD/CLP, construido con FastAPI.

## Características

- **Forecasts Multi-horizonte**: Predicciones a 7, 15, 30 y 90 días
- **Datos Históricos**: OHLC data de USD/CLP
- **Indicadores Técnicos**: RSI, MACD, Moving Averages, Bollinger Bands
- **Market Drivers**: Análisis de correlación con Cobre, DXY, Tasas
- **News Feed**: Noticias relevantes con análisis de sentimiento
- **Mock Data**: Datos simulados para desarrollo local
- **CORS Habilitado**: Para desarrollo con frontend

## Instalación

### Opción 1: Con Pipenv (Recomendado para desarrollo)

```bash
# Instalar pipenv si no lo tienes
pip install pipenv

# Navegar al directorio del API
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/api

# Instalar dependencias
pipenv install

# Activar el entorno virtual
pipenv shell
```

### Opción 2: Con pip

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Ejecución Local

### Con Pipenv

```bash
# Modo desarrollo (con hot reload)
pipenv run dev

# O directamente después de activar el shell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Con pip/venv

```bash
# Asegurarse de que el entorno virtual está activado
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El API estará disponible en: http://localhost:8000

## Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints Disponibles

### Forecasts

- `GET /api/forecasts` - Obtener todos los forecasts (7d, 15d, 30d, 90d)
- `GET /api/forecasts/{horizon}` - Forecast específico
- `GET /api/forecasts/accuracy/metrics` - Métricas de precisión histórica

### Historical Data

- `GET /api/historical?days=30` - Datos históricos OHLC

### Technical Indicators

- `GET /api/indicators` - Todos los indicadores técnicos
- `GET /api/indicators/summary` - Resumen simplificado con señales

### Market Drivers

- `GET /api/drivers` - Drivers del mercado (Cobre, DXY, etc.)
- `GET /api/drivers/summary` - Resumen de impacto agregado

### News

- `GET /api/news?limit=10&sentiment=positive` - Feed de noticias
- `GET /api/news/sentiment` - Análisis de sentimiento agregado
- `GET /api/news/trending` - Tópicos trending

### System

- `GET /api/health` - Health check del sistema
- `GET /api/statistics` - Estadísticas comprehensivas

## Estructura de Respuestas

### Forecast Response

```json
{
  "horizon": "7d",
  "horizon_days": 7,
  "current_price": 950.25,
  "forecast_price": 955.80,
  "price_change": 5.55,
  "price_change_pct": 0.58,
  "confidence_level": 0.95,
  "forecast_date": "2024-01-15T10:30:00",
  "data": [
    {
      "date": "2024-01-16",
      "value": 951.20,
      "lower_bound": 945.50,
      "upper_bound": 956.90
    }
  ],
  "metadata": {
    "model": "ARIMA",
    "accuracy_score": 0.92
  }
}
```

### Indicators Response

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "symbol": "USD/CLP",
  "current_price": 950.25,
  "indicators": [
    {
      "name": "RSI",
      "value": 55.5,
      "signal": "neutral",
      "strength": 0.11
    }
  ],
  "overall_signal": "buy",
  "overall_strength": 0.65
}
```

### News Response

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "count": 10,
  "articles": [
    {
      "id": "uuid",
      "title": "Fed mantiene tasas de interés",
      "summary": "La Fed decidió...",
      "source": "Reuters",
      "published_at": "2024-01-15T08:00:00",
      "relevance_score": 0.95,
      "sentiment": "neutral",
      "tags": ["Fed", "Tasas"]
    }
  ]
}
```

## Configuración

### Variables de Entorno

Crear un archivo `.env` en el directorio del API:

```env
# API Configuration
API_TITLE="Forex Forecast System API"
API_VERSION="1.0.0"
DEBUG=false

# Development Mode (usar mock data)
DEVELOPMENT_MODE=true

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# News API (opcional)
NEWS_API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO
```

## Deployment con Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Variables de entorno para producción
ENV DEVELOPMENT_MODE=false
ENV DATA_PATH=/app/data
ENV OUTPUT_PATH=/app/output

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    volumes:
      - /app/data:/app/data:ro
      - /app/output:/app/output:ro
    environment:
      - DEVELOPMENT_MODE=false
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

## Testing

```bash
# Ejecutar tests con pytest
pipenv run pytest

# Con coverage
pipenv run pytest --cov=.
```

## Desarrollo

### Agregar Nuevas Dependencias

```bash
# Con pipenv
pipenv install nombre_paquete

# Actualizar requirements.txt
pipenv requirements > requirements.txt
```

### Formateo y Linting

```bash
# Formatear código con black
pipenv run format

# Linting con flake8
pipenv run lint
```

## Integración con Frontend

El API está configurado con CORS para permitir requests desde el frontend en desarrollo:

```javascript
// Ejemplo en React/Next.js
const API_BASE_URL = 'http://localhost:8000/api';

// Obtener forecasts
const response = await fetch(`${API_BASE_URL}/forecasts`);
const data = await response.json();

// Con parámetros
const news = await fetch(`${API_BASE_URL}/news?limit=5&sentiment=positive`);
```

## Troubleshooting

### Error: ModuleNotFoundError

```bash
# Asegúrate de estar en el entorno virtual correcto
pipenv shell
# o
source venv/bin/activate
```

### CORS Issues

Verificar que el origen del frontend esté en `CORS_ORIGINS` en `.env`

### Puerto en uso

```bash
# Cambiar puerto
uvicorn main:app --port 8001
```

## Arquitectura

```
api/
├── main.py              # FastAPI app principal
├── routers/             # Endpoints organizados por dominio
│   ├── forecasts.py     # /api/forecasts/*
│   ├── indicators.py    # /api/indicators/*
│   ├── news.py          # /api/news/*
│   └── drivers.py       # /api/drivers/*
├── models/
│   └── schemas.py       # Modelos Pydantic para request/response
├── services/            # Lógica de negocio
│   ├── forecast_service.py  # Manejo de forecasts
│   ├── data_service.py      # Datos históricos e indicadores
│   └── news_service.py      # Servicio de noticias
└── utils/
    └── config.py        # Configuración centralizada
```

## Próximos Pasos

1. **Conectar con datos reales del servidor**:
   - Reemplazar mock data con lectura de archivos reales
   - Configurar paths de producción

2. **Agregar autenticación**:
   - JWT tokens
   - API keys para endpoints sensibles

3. **Caching**:
   - Redis para respuestas frecuentes
   - TTL configurable

4. **Websockets**:
   - Actualizaciones en tiempo real
   - Push notifications

5. **Monitoring**:
   - Prometheus metrics
   - Grafana dashboards

## Soporte

Para problemas o preguntas, revisar la documentación en `/docs` o contactar al equipo de desarrollo.