# Documentación para Retomar en 3 Semanas

**Fecha de creación:** 2025-11-13
**Fecha para retomar:** 2025-12-04 (3 semanas)
**Estado actual:** Copper integration deployado, esperando validación

---

## 🎯 Contexto: ¿Dónde estamos?

### Lo que se completó el 2025-11-13:

**1. Copper Price Integration** ✅ **DEPLOYADO EN PRODUCCIÓN**
- **Archivos creados:**
  - `src/forex_core/data/providers/copper_prices.py` (352 líneas)
  - `scripts/test_copper_integration.py` (246 líneas de tests)
  - `scripts/track_copper_impact.py` (719 líneas - tracking script)

- **Forecasters actualizados:**
  - ✅ forecaster-7d (rebuild + restart)
  - ✅ forecaster-15d (rebuild + restart)
  - ✅ forecaster-30d (rebuild + restart)
  - ✅ forecaster-90d (rebuild + restart)

- **Features implementadas:** 11 features de cobre
  1. `copper_returns_1d`, `copper_returns_5d`, `copper_returns_20d`
  2. `copper_volatility_20d`, `copper_volatility_60d`
  3. `copper_sma_20`, `copper_sma_50`, `copper_trend_signal`
  4. `copper_rsi_14`
  5. `copper_price_normalized`
  6. `copper_usdclp_corr_90d`

- **Fuente de datos:**
  - Primaria: Yahoo Finance (HG=F - COMEX Copper Futures)
  - Backup: FRED API (PCOPPUSDM - Global Price of Copper)
  - Cache: `data/warehouse/copper_hgf_usd_lb.parquet`

- **Claim de mejora:** +15-25% accuracy improvement
- **Estado:** ESPERANDO VALIDACIÓN (3 semanas de datos)

**2. Tracking Script Implementado** ✅
- Ubicación: `scripts/track_copper_impact.py`
- Propósito: Medir impacto real de copper integration
- Salidas:
  - `output/copper_impact_report_YYYYMMDD.json` (métricas)
  - `output/copper_impact_report_YYYYMMDD.html` (reporte visual)
- Frecuencia recomendada: Semanal

**3. Test de Email y PDF** ✅
- Script de prueba: `scripts/test_email_and_pdf.py`
- Archivos generados (en servidor):
  - `output/test_email_preview.html` (74KB)
  - `output/test_report_7d.pdf` (30KB)
- Estado: Validados visualmente, funcionando correctamente

---

## 📋 Tareas para Ejecutar en 3 Semanas (2025-12-04)

### Paso 1: Revisar Reportes Automáticos por Email

**✅ COMPLETAMENTE AUTOMATIZADO:** Los reportes te llegan por email cada domingo a las 10:00 AM.

**Destinatario:** rafael@cavara.cl

**Qué esperar en tu email:**
- Subject dinámico: "ℹ️ Copper Impact Report - Semana X - [STATUS]"
- Resumen ejecutivo con métricas clave
- Tabla de análisis por horizonte
- Reporte HTML completo adjunto
- Banner especial en semana 3+ (MILESTONE)

**No necesitas revisar el servidor** - Los reportes te llegarán automáticamente.

**Si quieres revisar manualmente en el servidor:**
```bash
# Reportes generados automáticamente cada semana
ssh reporting "ls -lht /home/deployer/forex-forecast-system/output/copper_impact_report_*.html | head -5"

# Descargar el más reciente
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.html output/

# Abrir localmente
open output/copper_impact_report_*.html  # macOS
```

**Verificar que cron y email están configurados:**
```bash
# Verifica que está configurado
ssh reporting "crontab -l | grep copper"

# Salida esperada:
# 0 10 * * 0 /home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh
```

**Logs del tracking automático:**
```bash
# Ver logs de ejecuciones
ssh reporting "cat /home/deployer/forex-forecast-system/logs/copper_tracking.log | tail -50"

# Ver historial de cron
ssh reporting "cat /home/deployer/forex-forecast-system/logs/copper_tracking_cron.log"
```

**Ejecución manual (si necesitas):**
```bash
# Solo si quieres ejecutar fuera del schedule semanal
ssh reporting "/home/deployer/forex-forecast-system/scripts/weekly_copper_tracking.sh"
```

### Paso 2: Analizar Resultados

**Criterios de Éxito:**

| Métrica | Target | Interpretación |
|---------|--------|----------------|
| **RMSE Improvement** | -15% a -25% | Reducción en error promedio |
| **Directional Accuracy** | >= 60% | % predicciones con dirección correcta |
| **Horizons Improved** | >= 3 de 4 | Cuántos horizontes mejoraron |

**Decisiones basadas en resultados:**

1. **Si mejora >= 15%:** ✅ SUCCESS
   - ✅ Copper integration exitosa
   - ➡️ Continuar con **Fase 2: Treasury Yields + IPSA**

2. **Si mejora 5-15%:** ⚠️ PARTIAL SUCCESS
   - ⚠️ Mejora moderada detectada
   - ➡️ Esperar 1 semana más o proceder con cautela

3. **Si mejora < 5%:** ❌ MINIMAL/NO IMPROVEMENT
   - ❌ Investigar causas:
     - ¿Datos de copper llegando correctamente?
     - ¿Features correctamente calculados?
     - ¿Correlación copper-USD/CLP se mantiene?
   - ➡️ Considerar:
     - Feature engineering adicional (term structure, export volumes)
     - Ajustar features existentes
     - O revertir copper integration

### Paso 3: Si Copper Exitoso → Fase 2

**Implementar en este orden (2-3 días cada uno):**

1. **US Treasury Yields** (Prioridad MÁXIMA)
   ```python
   # Crear: src/forex_core/data/providers/treasury_yields.py
   # Features: 2Y, 10Y yields, 10Y-2Y spread, Chile-US differential
   # Impacto esperado: +12-18% accuracy
   # Esfuerzo: 1 día (ya tienes FredClient)
   ```

2. **IPSA Index** (Prioridad ALTA)
   ```python
   # Crear: src/forex_core/data/providers/ipsa_index.py
   # Features: Returns, volatility, trend, drawdown
   # Impacto esperado: +10-15% accuracy
   # Esfuerzo: 1-2 días (similar a copper)
   ```

3. **Interaction Features** (Quick Win)
   ```python
   # Agregar a DataLoader: compute_interaction_features()
   # Features: copper×VIX, copper×DXY, IPSA×copper
   # Impacto esperado: +5-8% accuracy
   # Esfuerzo: 1-2 días
   ```

**Impacto acumulado esperado:** +27-41% accuracy improvement

---

## 🚀 Roadmap Completo (Próximos 3 Meses)

```
DICIEMBRE 2025:
├─ Semana 1 (Dic 4): Validar copper impact
├─ Semana 2-3: Treasury Yields + IPSA (si copper exitoso)
├─ Semana 4: MLflow deployment (forecaster 7d piloto)
└─ Resultado: 3 nuevas fuentes de datos integradas

ENERO 2026:
├─ Semana 1-2: MLflow rollout (15d, 30d, 90d)
├─ Semana 3-4: Auto-retraining Docker integration
└─ Resultado: MLflow tracking operacional

FEBRERO 2026:
├─ Semana 1-2: Auto-retraining testing exhaustivo
├─ Semana 3-4: Automatización con cron
└─ Resultado: Auto-retraining pipeline productivo

MARZO 2026+:
├─ Gold prices integration
├─ China PMI integration
├─ Regime detection
└─ Ensemble diversification
```

---

## 📚 Documentación Clave

**Documentos a revisar antes de retomar:**

1. **`docs/HIGH_IMPACT_IMPROVEMENTS_SUMMARY.md`**
   - Resumen completo de las 3 mejoras implementadas
   - 392 líneas, overview de todo el proyecto

2. **`docs/COPPER_INTEGRATION.md`**
   - Detalles técnicos de copper integration
   - 444 líneas, guía completa

3. **`docs/QUICK_DEPLOY.md`**
   - Guía de deployment rápido
   - 423 líneas, instrucciones paso a paso

4. **`docs/sessions/2025-11-13-HIGH-IMPACT-IMPROVEMENTS.md`**
   - Log de la sesión completa
   - 1,137 líneas, contexto detallado

**Consultas rápidas de agentes expertos:**

Las recomendaciones de los agentes @agent-ml-expert y @agent-usdclp están guardadas en esta sesión. Puntos clave:

- **ml-expert:** Enfatiza validación empírica antes de agregar complejidad
- **usdclp:** Recomienda Treasury Yields como próxima prioridad máxima

---

## 🔧 Comandos Útiles para Retomar

### Verificar Estado del Sistema

```bash
# 1. Estado de contenedores
ssh reporting "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep forecaster"

# 2. Logs recientes de forecaster 7d
ssh reporting "docker logs --tail=100 usdclp-forecaster-7d | grep -i copper"

# 3. Verificar datos de copper
ssh reporting "ls -lh /home/deployer/forex-forecast-system/data/warehouse/copper_hgf_usd_lb.parquet"

# 4. Ver últimos reportes generados
ssh reporting "ls -lht /home/deployer/forex-forecast-system/reports/*.pdf | head -5"
```

### Ejecutar Tracking (en servidor)

```bash
# Opción 1: Ejecución directa en servidor
ssh reporting "cd /home/deployer/forex-forecast-system && python3 scripts/track_copper_impact.py"

# Opción 2: Descargar datos y ejecutar localmente
scp reporting:/home/deployer/forex-forecast-system/data/predictions/predictions.parquet data/predictions/
python scripts/track_copper_impact.py

# Descargar reportes generados
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.html output/
scp reporting:/home/deployer/forex-forecast-system/output/copper_impact_report_*.json output/

# Abrir reporte
open output/copper_impact_report_*.html
```

### Si Necesitas Revertir Copper

```bash
# 1. Backup de configuración actual
ssh reporting "cd /home/deployer/forex-forecast-system && git add -A && git commit -m 'backup before copper revert'"

# 2. Revertir cambios en loader.py
# (Eliminar líneas de copper integration manualmente)

# 3. Rebuild contenedores
ssh reporting "cd /home/deployer/forex-forecast-system && docker compose -f docker-compose.prod.yml build forecaster-7d forecaster-15d forecaster-30d forecaster-90d"

# 4. Restart contenedores
ssh reporting "cd /home/deployer/forex-forecast-system && docker compose -f docker-compose.prod.yml up -d forecaster-7d forecaster-15d forecaster-30d forecaster-90d"
```

---

## 📊 Métricas Baseline (Pre-Copper)

**Importante:** Estas son las métricas pre-copper para comparar:

```
# Si no las tienes guardadas, ejecutar backtest sin copper features:
# (Modificar temporalmente DataLoader para omitir copper_features)

Baseline RMSE (aproximado, validar con datos reales):
- 7d:  8-10 CLP
- 15d: 10-12 CLP
- 30d: 12-15 CLP
- 90d: 15-20 CLP

Target Post-Copper:
- 7d:  6.8-8.5 CLP  (-15% a -25%)
- 15d: 8.5-10.2 CLP (-15% a -25%)
- 30d: 10.2-12.8 CLP (-15% a -25%)
- 90d: 12.8-17.0 CLP (-15% a -25%)
```

---

## ⚠️ Problemas Potenciales y Soluciones

### Problema 1: Tracking Script No Encuentra Datos

**Síntoma:** `predictions.parquet` vacío o no existe

**Solución:**
```bash
# Verificar que forecasters hayan ejecutado
ssh reporting "docker logs usdclp-forecaster-7d --tail=200"

# Verificar cron jobs
ssh reporting "crontab -l | grep forecaster"

# Ejecutar forecaster manualmente si es necesario
ssh reporting "docker exec usdclp-forecaster-7d python -m services.forecaster_7d.cli run"
```

### Problema 2: Copper Data No Se Actualiza

**Síntoma:** `last_update` en copper_health es antiguo

**Solución:**
```bash
# 1. Verificar logs de fetching
ssh reporting "docker logs usdclp-forecaster-7d 2>&1 | grep -i 'copper'"

# 2. Verificar conectividad a Yahoo Finance
ssh reporting "curl -I https://finance.yahoo.com"

# 3. Verificar FRED API key (backup)
ssh reporting "cat /home/deployer/forex-forecast-system/.env | grep FRED_API_KEY"

# 4. Forzar refresh eliminando cache
ssh reporting "rm /home/deployer/forex-forecast-system/data/warehouse/copper_hgf_usd_lb.parquet"
# Próxima ejecución reconstruirá cache
```

### Problema 3: Mejora < 5% (No Improvement)

**Posibles causas y diagnóstico:**

1. **Datos de copper incorrectos**
   - Verificar `data/warehouse/copper_hgf_usd_lb.parquet`
   - Validar que precios tienen sentido ($3-5/lb típicamente)

2. **Features mal calculadas**
   - Ejecutar `scripts/test_copper_integration.py`
   - Verificar que 10 features se computan sin NaN

3. **Correlación débil en período evaluado**
   - Analizar correlación copper-USD/CLP rolling 90d
   - Chile puede haber tenido otros drivers dominantes

4. **Modelo no usa features**
   - Chronos es pre-trained, puede ignorar algunas features
   - Considerar feature engineering adicional

**Acción:** Ver sección "Advanced Features" en docs de agente usdclp

---

## 🎯 Objetivos Claros para Sesión de Retoma

**Al retomar el 2025-12-04, debes:**

1. ✅ Ejecutar `track_copper_impact.py`
2. ✅ Analizar reporte HTML generado
3. ✅ Tomar decisión GO/NO-GO basada en métricas
4. ✅ Si GO: Implementar Treasury Yields (1 día)
5. ✅ Si NO-GO: Diagnosticar y ajustar copper features

**Preguntas clave a responder:**

- [ ] ¿Copper mejoró RMSE en >= 15%?
- [ ] ¿Qué features de copper son más importantes?
- [ ] ¿Hay horizontes donde copper ayuda más?
- [ ] ¿Deberíamos continuar con Treasury Yields?

---

## 📞 Contacto y Recursos

**Archivos críticos (no modificar sin backup):**
- `src/forex_core/data/loader.py` (integración de copper)
- `src/forex_core/data/providers/copper_prices.py` (proveedor de copper)
- `configs/chronos_*.json` (configuraciones de modelo)

**Backups automáticos:**
- Git commits: Todo está committeado en `develop` branch
- Docker images: Imágenes anteriores disponibles
- Configs: `configs/backups/` (si se usa auto-retraining)

**En caso de emergencia:**
- Logs: `logs/*.log`
- Docker logs: `docker logs <container_name>`
- Servidor: ssh reporting
- Rollback: git revert último commit

---

## ✅ Checklist Pre-Retoma

Antes de la sesión del 2025-12-04, asegúrate de tener:

- [ ] Acceso al servidor VPS (ssh reporting)
- [ ] Ambiente local actualizado (git pull)
- [ ] Dependencias instaladas (requirements.txt)
- [ ] 30-60 minutos disponibles para análisis
- [ ] Este documento abierto como referencia

---

**Última actualización:** 2025-11-13 23:25 (Chile)
**Próxima revisión:** 2025-12-04
**Autor:** session-doc-keeper + ml-expert + usdclp-expert
**Versión:** 1.0
