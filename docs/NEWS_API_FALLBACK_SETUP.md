# Configuración del Sistema de Fallback Multi-Fuente para Noticias

## 🎯 Objetivo

Implementar un sistema resiliente de noticias que **nunca falle**, incluso cuando las APIs externas tengan problemas (429 rate limits, timeouts, etc.).

## 🏗️ Arquitectura del Sistema

### Cadena de Fallback Automático

El sistema intenta múltiples fuentes en orden hasta que una funcione:

```
1. NewsAPI.org (100 requests/día)
   ↓ Si falla (429, timeout, etc.)
2. NewsData.io (200 requests/día)
   ↓ Si falla
3. RSS Feeds (ilimitado, siempre disponible)
   ↓ Si falla
4. Lista vacía (no-blocking - el pronóstico continúa sin noticias)
```

### Características

- ✅ **Retry logic** con exponential backoff (1s, 2s, 4s)
- ✅ **Caché de 6 horas** para reducir requests
- ✅ **Non-blocking** - nunca causa que el forecast falle
- ✅ **Logging completo** para troubleshooting
- ✅ **Manejo graceful de 429 errors** - no hace retry en rate limits

## 📝 Configuración Paso a Paso

### Paso 1: Obtener API Key de NewsData.io

1. **Registrarse**: Ve a https://newsdata.io/register
2. **Verificar email**: Confirma tu cuenta
3. **Copiar API Key**: En el dashboard, copia tu API key

**Plan gratuito:**
- 200 requests/día
- Sin necesidad de tarjeta de crédito
- Perfecto como fallback

### Paso 2: Agregar API Key al .env

En el servidor Vultr, agrega la clave al archivo `.env`:

```bash
ssh reporting
cd /home/deployer/forex-forecast-system
nano .env
```

Agrega esta línea:

```bash
# NewsData.io API Key (fallback news source)
NEWSDATA_API_KEY=tu_api_key_aqui
```

Guarda y cierra (Ctrl+O, Enter, Ctrl+X).

### Paso 3: Verificar Configuración

```bash
# Verificar que la variable esté configurada
grep NEWSDATA /home/deployer/forex-forecast-system/.env

# Debería mostrar:
# NEWSDATA_API_KEY=tu_clave_real
```

## 🔧 Archivos Modificados/Creados

### Nuevos Providers

1. **src/forex_core/data/providers/newsdata_io.py**
   - Cliente para NewsData.io API
   - 200 requests/día (plan gratuito)
   - Análisis de sentiment

2. **src/forex_core/data/providers/rss_news.py**
   - Cliente RSS (sin límites)
   - Fuentes: Diario Financiero, La Tercera, Emol, BioBio
   - Filtrado por keywords económicas chilenas

3. **src/forex_core/data/providers/news_aggregator.py**
   - Orquestador multi-fuente
   - Fallback automático
   - Retry logic y caché

### Archivos Modificados

1. **src/forex_core/config/base.py**
   - Agregado campo `newsdata_api_key`

2. **src/forex_core/data/loader.py**
   - Reemplazado `NewsApiClient` por `NewsAggregator`
   - Método `_news()` ahora es resiliente

3. **.env.example**
   - Documentado `NEWSDATA_API_KEY`

## 🧪 Testing

### Test Local

```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
source venv/bin/activate
python test_news_fallback.py
```

**Salida esperada:**

```
======================================================================
TESTING MULTI-SOURCE NEWS AGGREGATOR WITH FALLBACK
======================================================================

📋 Configured API Keys:
  - NEWS_API_KEY: ✓ Set
  - NEWSDATA_API_KEY: ✓ Set

🔧 Initializing NewsAggregator...

📊 Provider Status:
  ✓ NewsAPI.org: available
  ✓ NewsData.io: available
  ✓ RSS Feeds: available

📰 Fetching news with automatic fallback...
----------------------------------------------------------------------

✅ SUCCESS: Fetched 15 headlines

Sample headlines:

1. [Positivo] Cobre sube por optimismo en demanda china
   Source: NewsData.io
   Published: 2025-11-13 18:30:00+00:00

...

======================================================================
✓ Test completed successfully
  The system is resilient and will not fail even when APIs are down.
======================================================================
```

### Test en Producción (Vultr)

```bash
ssh reporting
cd /home/deployer/forex-forecast-system
source venv/bin/activate
PYTHONPATH=src python test_news_fallback.py
```

## 🚀 Deployment

### Paso 1: Commit y Push

```bash
git add .
git commit -m "feat: Add multi-source news fallback system with NewsData.io

- Implements NewsData.io provider (200 requests/day)
- Implements RSS feed provider (unlimited)
- Creates NewsAggregator with automatic fallback
- Updates loader.py to use resilient news fetching
- System never fails due to news API issues

Fixes forecaster-7d infinite restart loop caused by NewsAPI 429 errors.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin develop
```

### Paso 2: Pull en Vultr

```bash
ssh reporting
cd /home/deployer/forex-forecast-system
git pull origin develop
```

### Paso 3: Rebuild Docker Images

```bash
cd /home/deployer/forex-forecast-system

# Rebuild forecaster-7d image
docker-compose -f docker-compose.prod.yml build forecaster-7d

# Rebuild otros forecasters que usan news (opcional)
docker-compose -f docker-compose.prod.yml build forecaster-15d forecaster-30d
```

### Paso 4: Restart Containers

```bash
# Start forecaster-7d
docker-compose -f docker-compose.prod.yml up -d forecaster-7d

# Verificar que esté corriendo
docker ps | grep forecaster-7d

# Ver logs
docker logs usdclp-forecaster-7d --tail 50 --follow
```

## 📊 Monitoreo

### Verificar Logs

```bash
# Ver logs del container 7d
docker logs usdclp-forecaster-7d --tail 100

# Buscar mensajes de éxito
docker logs usdclp-forecaster-7d 2>&1 | grep "Successfully fetched"

# Buscar errores de news
docker logs usdclp-forecaster-7d 2>&1 | grep -i "news"
```

### Verificar que no haya 429 errors

```bash
# Buscar 429 errors
docker logs usdclp-forecaster-7d 2>&1 | grep "429"

# Si no hay output, ¡perfecto!
```

### Estado del Container

```bash
# Ver estado
docker ps -a | grep forecaster-7d

# Debería mostrar:
# STATUS: Up X minutes (healthy)
# No más "Restarting"
```

## 🔍 Troubleshooting

### Problema: Forecaster sigue reiniciando

**Causa posible:** NewsData.io API key no configurada correctamente

**Solución:**

```bash
# 1. Verificar .env
cat /home/deployer/forex-forecast-system/.env | grep NEWSDATA

# 2. Rebuild image para que tome nuevo .env
docker-compose -f docker-compose.prod.yml build forecaster-7d

# 3. Restart con nueva imagen
docker-compose -f docker-compose.prod.yml up -d forecaster-7d
```

### Problema: No se encuentran noticias

**Es normal!** El sistema es resiliente:

```
⚠️ All news providers failed or returned no data.
Continuing forecast without news data.
```

Esto **NO es un error** - el pronóstico continúa sin noticias.

### Problema: RSS feeds fallan

**También es normal!** RSS feeds son el último fallback. Si NewsAPI y NewsData.io funcionan, los RSS no se necesitan.

## 📈 Consumo de API

### Con Fallback Implementado

- **NewsAPI:** ~1 request/día (solo 7d diario)
- **NewsData.io:** ~0-1 request/día (solo cuando NewsAPI falla)
- **RSS:** ~0-4 requests/día (solo cuando ambas APIs fallan)

**Total esperado:** ~1-2 requests/día (muy por debajo de límites)

### Antes del Fallback

- **NewsAPI:** ~1,440 requests/día (loop infinito)
- **Resultado:** Rate limit excedido, forecaster fails

## ✅ Checklist de Deployment

- [ ] API key de NewsData.io obtenida
- [ ] `NEWSDATA_API_KEY` agregada al `.env` en Vultr
- [ ] Código commiteado y pusheado a GitHub
- [ ] Pull realizado en Vultr
- [ ] Docker images rebuilt
- [ ] Container forecaster-7d reiniciado
- [ ] Logs verificados (sin 429 errors)
- [ ] Container en estado "healthy"
- [ ] Test de forecast completado exitosamente

## 🎉 Resultado Final

El sistema ahora es **production-ready** y resiliente:

- ✅ Nunca falla por problemas de APIs externas
- ✅ Fallback automático transparente
- ✅ Manejo graceful de rate limits
- ✅ Logging completo para debugging
- ✅ Caché para reducir requests
- ✅ No requiere intervención manual

**El forecaster-7d debería correr stable 24/7 sin reiniciarse.**
