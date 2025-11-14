# Cleanup Plan - Archivos a Eliminar

Este documento lista todos los archivos relacionados con Chronos y código obsoleto que serán eliminados del repositorio.

**IMPORTANTE**: Requiere aprobación del usuario antes de eliminar.

---

## 1. Archivos de Chronos (15 archivos)

### Core Implementation
- [ ] `src/forex_core/forecasting/chronos_model.py` - Modelo Chronos-T5 principal
- [ ] `src/forex_core/optimization/chronos_optimizer.py` - Optimizador de Chronos
- [ ] `src/forex_core/models/chronos_to_interpretable_migration.py` - Script de migración

### Scripts y Examples
- [ ] `examples/test_chronos_integration.py` - Test de integración
- [ ] `examples/test_chronos_simple.py` - Test simple
- [ ] `examples/README_CHRONOS.md` - README de examples
- [ ] `scripts/check_chronos_readiness.py` - Script de validación

### Documentación
- [ ] `docs/CHRONOS_INTEGRATION.md` - Documentación de integración
- [ ] `docs/CHRONOS_PRODUCTION_DEPLOYMENT.md` - Guía de deployment
- [ ] `docs/CHRONOS_IMPLEMENTATION_SUMMARY.md` - Resumen de implementación
- [ ] `docs/CHRONOS_AUTO_VALIDATION.md` - Validación automática
- [ ] `CHRONOS_DEPLOYMENT_CHECKLIST.md` - Checklist de deployment
- [ ] `docs/conversations/2025-11-13-chronos-readiness-automation-setup.md` - Conversación

### Data Files
- [ ] `data/chronos_readiness_status.txt` - Status file

### Cache Files
- [ ] `src/forex_core/forecasting/__pycache__/chronos_model.cpython-312.pyc` - Python cache

---

## 2. Scripts Obsoletos (1 archivo)

- [ ] `scripts/validate_model.py` - Validación con modelo naive (obsoleto, ahora usamos walk-forward validation)

---

## 3. Archivos a Modificar (NO eliminar, solo limpiar referencias)

### Actualizar referencias a Chronos:
- [ ] `src/forex_core/config/base.py` - Remover configuración de Chronos
- [ ] `src/forex_core/optimization/validator.py` - Remover validador de Chronos
- [ ] `src/forex_core/optimization/deployment.py` - Remover deployment de Chronos
- [ ] `src/forex_core/optimization/__init__.py` - Remover exports de Chronos
- [ ] `src/forex_core/mlops/mlflow_config.py` - Remover tracking de Chronos
- [ ] `src/forex_core/mlops/readiness.py` - Remover readiness checks de Chronos
- [ ] `src/forex_core/forecasting/models.py` - Remover clase ChronosForecaster
- [ ] `src/forex_core/forecasting/__init__.py` - Remover exports de Chronos
- [ ] `src/services/model_optimizer/pipeline.py` - Remover optimización de Chronos
- [ ] `scripts/init_mlflow.py` - Remover tracking de Chronos

### Actualizar requirements.txt:
- [ ] `requirements.txt` - Remover línea: `chronos-forecasting>=1.2.0,<2.0.0`
- [ ] `requirements.txt` - Remover línea: `torch>=2.0.0` (si no se usa para otra cosa)

---

## 4. Archivos que NO se tocan (críticos)

✅ **PRESERVAR ESTOS ARCHIVOS** (no eliminar):
- `scripts/test_email_and_pdf.py` - Generación de emails y PDFs (CRÍTICO)
- `scripts/send_daily_email.sh` - Script de envío de emails
- Cualquier archivo de configuración de email
- Cualquier archivo del sistema de emails unificado

---

## 5. Resumen de Eliminación

**Total a eliminar**: 16 archivos
- Código fuente: 3 archivos
- Scripts: 3 archivos
- Documentación: 9 archivos
- Data: 1 archivo
- Cache: 1 archivo (pycache)

**Total a modificar**: 10 archivos (solo limpiar referencias)

**Total preservado**: Todo el sistema de emails y PDFs

---

## 6. Plan de Ejecución

### Paso 1: Backup
```bash
# Crear backup antes de eliminar
tar -czf backup_chronos_$(date +%Y%m%d).tar.gz \
  src/forex_core/forecasting/chronos_model.py \
  src/forex_core/optimization/chronos_optimizer.py \
  examples/test_chronos_*.py \
  docs/CHRONOS_*.md
```

### Paso 2: Eliminar Archivos
```bash
# Eliminar código
rm src/forex_core/forecasting/chronos_model.py
rm src/forex_core/optimization/chronos_optimizer.py
rm src/forex_core/models/chronos_to_interpretable_migration.py

# Eliminar scripts
rm examples/test_chronos_integration.py
rm examples/test_chronos_simple.py
rm examples/README_CHRONOS.md
rm scripts/check_chronos_readiness.py

# Eliminar documentación
rm docs/CHRONOS_INTEGRATION.md
rm docs/CHRONOS_PRODUCTION_DEPLOYMENT.md
rm docs/CHRONOS_IMPLEMENTATION_SUMMARY.md
rm docs/CHRONOS_AUTO_VALIDATION.md
rm CHRONOS_DEPLOYMENT_CHECKLIST.md
rm docs/conversations/2025-11-13-chronos-readiness-automation-setup.md

# Eliminar data
rm data/chronos_readiness_status.txt

# Limpiar cache
find . -name "*chronos*.pyc" -delete
find . -type d -name "__pycache__" -empty -delete
```

### Paso 3: Limpiar Referencias
Usar herramientas de refactoring o búsqueda/reemplazo para:
1. Remover imports de chronos
2. Remover clases y funciones relacionadas
3. Actualizar requirements.txt

### Paso 4: Commit
```bash
git add -A
git commit -m "refactor: Remove Chronos-T5 implementation, migrate to XGBoost+SARIMAX+GARCH ensemble

- Remove Chronos model implementation and related files
- Remove Chronos optimization and validation scripts
- Remove Chronos documentation
- Update requirements.txt (remove chronos-forecasting, torch)
- Clean up references in core modules

This completes the migration to interpretable models as per Phase 1-4 implementation plan."
```

---

## 7. Verificación Post-Cleanup

Después de eliminar, verificar que:

```bash
# No quedan referencias a chronos
grep -r "chronos" src/ scripts/ --include="*.py" | grep -v ".pyc" | grep -v "__pycache__"

# No quedan imports de chronos
grep -r "from.*chronos" src/ scripts/ --include="*.py"
grep -r "import.*chronos" src/ scripts/ --include="*.py"

# Sistema de emails intacto
ls -la scripts/test_email_and_pdf.py
ls -la scripts/send_daily_email.sh

# Nuevos modelos presentes
ls -la src/forex_core/models/xgboost_forecaster.py
ls -la src/forex_core/models/sarimax_forecaster.py
ls -la src/forex_core/models/garch_volatility.py
ls -la src/forex_core/models/ensemble_forecaster.py
```

---

## 8. Estado Actual

**Fecha**: 2025-11-14
**Estado**: PENDIENTE APROBACIÓN
**Ejecutado**: NO

---

## 9. Aprobación Requerida

Por favor revisar este plan y aprobar antes de ejecutar:

- [ ] Apruebo eliminar todos los archivos de Chronos listados arriba
- [ ] Apruebo limpiar las referencias en archivos a modificar
- [ ] Apruebo actualizar requirements.txt
- [ ] Confirmo que el sistema de emails NO debe tocarse

**Firma**: _____________________
**Fecha**: _____________________

---

**Siguiente paso**: Una vez aprobado, ejecutar el cleanup automáticamente o manualmente según prefieras.
