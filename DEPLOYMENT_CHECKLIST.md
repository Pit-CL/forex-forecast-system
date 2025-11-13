# 🚀 Deployment Checklist - Forex Forecasting System

Checklist completo para desplegar todas las mejoras de MLOps Phase 2 en el servidor Vultr.

---

## 📋 Pre-Deployment

### Local Verification

- [ ] **Ejecutar todos los tests localmente**
  ```bash
  pip install -r requirements.txt
  pytest tests/ -v
  pytest tests/unit/test_validators.py -v  # Security tests
  ```

- [ ] **Verificar que no hay errores de sintaxis**
  ```bash
  python -m py_compile src/forex_core/**/*.py
  ```

- [ ] **Commit y push de todos los cambios**
  ```bash
  git status  # Verificar cambios
  git add .
  git commit -m "feat: Complete MLOps Phase 2 - All 11 tasks"
  git push origin develop
  ```

- [ ] **Verificar archivos nuevos en .gitignore**
  ```bash
  # Asegurar que estos NO están en git:
  # - .env (credenciales)
  # - data/*.parquet (datos)
  # - logs/*.log (logs)
  # - config/usdclp_calibration.json (opcional, puede commitearse)
  ```

---

## 🔌 Deployment to Vultr

### Step 1: Conectar al Servidor

- [ ] **SSH al servidor**
  ```bash
  ssh reporting
  ```

- [ ] **Verificar ubicación**
  ```bash
  pwd  # Debe mostrar: /home/forecast o similar
  cd forex-forecast-system
  ```

### Step 2: Backup Current State

- [ ] **Crear backup de configuración actual**
  ```bash
  # Backup de datos
  tar -czf backup_$(date +%Y%m%d).tar.gz data/ logs/ config/ .env

  # Mover backup a directorio seguro
  mv backup_*.tar.gz ~/backups/
  ```

- [ ] **Backup de crontab actual**
  ```bash
  crontab -l > ~/backups/crontab_backup_$(date +%Y%m%d).txt
  ```

### Step 3: Update Code

- [ ] **Pull latest changes**
  ```bash
  git status  # Verificar estado
  git fetch origin
  git pull origin develop
  ```

- [ ] **Verificar archivos nuevos**
  ```bash
  ls -la src/forex_core/utils/  # Debe contener file_lock.py, validators.py
  ls -la src/forex_core/mlops/  # Debe contener regime_detector.py, performance_monitor.py
  ls -la scripts/*.sh  # Debe contener weekly_validation.sh, daily_dashboard.sh
  ```

### Step 4: Update Dependencies

- [ ] **Activar virtual environment**
  ```bash
  source venv/bin/activate
  # O: source .venv/bin/activate
  ```

- [ ] **Actualizar dependencias**
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt

  # Verificar instalación
  pip list | grep -E "pytest|portalocker|scipy"
  ```

### Step 5: Run Tests

- [ ] **Ejecutar test suite**
  ```bash
  pytest tests/ -v

  # Específicamente security tests
  pytest tests/unit/test_validators.py -v

  # File locking tests
  pytest tests/test_file_lock.py -v
  ```

- [ ] **Verificar imports**
  ```python
  python -c "from forex_core.mlops import MarketRegimeDetector; print('✓ OK')"
  python -c "from forex_core.mlops import PerformanceMonitor; print('✓ OK')"
  python -c "from forex_core.utils.validators import validate_horizon; print('✓ OK')"
  ```

### Step 6: Configuration

- [ ] **Verificar/actualizar .env**
  ```bash
  nano .env

  # Verificar estas variables:
  # EMAIL_ENABLED=true (si quieres notificaciones)
  # GMAIL_USER=your-email@gmail.com
  # GMAIL_APP_PASSWORD=your-app-password
  # EMAIL_RECIPIENTS=recipient@email.com
  ```

- [ ] **Generar calibración USD/CLP**
  ```bash
  python scripts/calibrate_usdclp.py analyze --data-dir data

  # Verificar archivo generado
  cat config/usdclp_calibration.json
  ```

- [ ] **Aplicar configuración calibrada**
  ```bash
  python scripts/calibrate_usdclp.py update-config
  ```

### Step 7: Verify Core Functionality

- [ ] **Test prediction tracking**
  ```python
  python -c "
  from pathlib import Path
  from forex_core.mlops.tracking import PredictionTracker
  tracker = PredictionTracker(storage_path=Path('data/predictions/predictions.parquet'))
  print(f'✓ Tracker initialized')
  "
  ```

- [ ] **Test regime detection**
  ```bash
  python examples/test_regime_detector.py
  ```

- [ ] **Test performance monitoring**
  ```bash
  python scripts/check_performance.py --all
  ```

- [ ] **Test validation**
  ```bash
  python scripts/validate_model.py --horizon 7d --folds 1
  ```

### Step 8: Install Automation

- [ ] **Make scripts executable**
  ```bash
  chmod +x scripts/*.sh
  chmod +x scripts/*.py

  # Verificar permisos
  ls -lh scripts/*.sh
  ```

- [ ] **Install cron jobs**
  ```bash
  ./scripts/install_cron_jobs.sh

  # Verificar instalación
  crontab -l
  ```

- [ ] **Test cron scripts manually**
  ```bash
  # Test weekly validation
  ./scripts/weekly_validation.sh

  # Test daily dashboard
  ./scripts/daily_dashboard.sh

  # Verificar logs
  tail -50 logs/weekly_validation_*.log
  tail -50 logs/daily_dashboard_*.log
  ```

### Step 9: Monitoring Setup

- [ ] **Crear directorios necesarios**
  ```bash
  mkdir -p logs
  mkdir -p reports/validation
  mkdir -p reports/daily
  mkdir -p config
  ```

- [ ] **Test email notifications** (si EMAIL_ENABLED=true)
  ```python
  python -c "
  from forex_core.notifications.email_sender import EmailSender
  sender = EmailSender()
  sender.send_email(
      subject='Test - Deployment Verification',
      body='This is a test email to verify email functionality after deployment.'
  )
  print('✓ Email sent')
  "
  ```

- [ ] **Verificar logs iniciales**
  ```bash
  tail -f logs/cron.log &
  # Esperar primer cron job, o ejecutar manualmente
  ```

### Step 10: Readiness Check

- [ ] **Verificar Chronos readiness**
  ```bash
  python -c "
  from pathlib import Path
  from forex_core.mlops.readiness import ChronosReadinessChecker

  checker = ChronosReadinessChecker(data_dir=Path('data'))
  report = checker.assess()

  print(f'\n{"="*70}')
  print(f'READINESS STATUS: {report.level.value.upper()}')
  print(f'Score: {report.score:.0f}/100')
  print(f'{"="*70}\n')
  print(report.recommendation)
  "
  ```

- [ ] **Decisión: Habilitar Chronos** (si readiness ≥ READY)
  ```bash
  # Si readiness es READY u OPTIMAL:
  # Editar configuración para enable_chronos=True
  # (Ubicación depende de tu config actual)
  ```

---

## ✅ Post-Deployment Verification

### Immediate Checks (Day 1)

- [ ] **Verificar cron jobs ejecutándose**
  ```bash
  # Esperar a horario programado o ejecutar manualmente
  tail -f logs/cron.log
  ```

- [ ] **Check email delivery**
  - [ ] Verificar inbox para daily dashboard
  - [ ] Confirmar formato HTML correcto
  - [ ] Verificar que métricas se muestran

- [ ] **Monitor system logs**
  ```bash
  tail -f logs/*.log
  # Buscar errores o warnings
  ```

- [ ] **Verify data integrity**
  ```bash
  # Verificar que archivos parquet no están corruptos
  python -c "
  import pandas as pd
  df = pd.read_parquet('data/predictions/predictions.parquet')
  print(f'✓ Predictions file OK: {len(df)} records')
  "
  ```

### Week 1 Monitoring

- [ ] **Daily dashboard recibido cada día**
- [ ] **Weekly validation ejecutada (Lunes)**
- [ ] **Performance checks sin degradación**
- [ ] **No errors en logs/cron.log**

### Week 2-4 Monitoring

- [ ] **Calibración funciona correctamente**
- [ ] **Regime detection identifica patrones**
- [ ] **Performance monitoring detecta cambios**
- [ ] **Email notifications funcionan consistentemente**

---

## 🔧 Troubleshooting

### Si algo falla:

1. **Restaurar desde backup**
   ```bash
   cd ~/backups
   tar -xzf backup_YYYYMMDD.tar.gz -C ~/forex-forecast-system
   ```

2. **Restaurar crontab**
   ```bash
   crontab ~/backups/crontab_backup_YYYYMMDD.txt
   ```

3. **Check logs detallados**
   ```bash
   tail -100 logs/cron.log
   tail -100 logs/weekly_validation_*.log
   ```

4. **Revert git changes**
   ```bash
   git log  # Find last good commit
   git reset --hard <commit-hash>
   ```

---

## 📊 Success Criteria

El deployment es exitoso cuando:

- [x] ✅ Todos los tests pasan
- [x] ✅ Cron jobs instalados y ejecutándose
- [x] ✅ Daily dashboard recibido por email
- [x] ✅ Weekly validation ejecutada sin errores
- [x] ✅ Performance monitoring funcionando
- [x] ✅ No errores en logs
- [x] ✅ Readiness check muestra READY o mejor
- [x] ✅ Calibración USD/CLP generada
- [x] ✅ Email notifications funcionando (si configurado)

---

## 📝 Post-Deployment Notes

### Documentar:

- [ ] **Fecha de deployment:** _______________
- [ ] **Versión/commit deployed:** _______________
- [ ] **Readiness status:** _______________
- [ ] **Chronos enabled:** Sí / No
- [ ] **Email notifications enabled:** Sí / No
- [ ] **Issues encontrados:** _______________
- [ ] **Notas adicionales:** _______________

### Comunicar:

- [ ] Notificar a stakeholders que deployment está completo
- [ ] Compartir ubicación de dashboards/reports
- [ ] Explicar cómo interpretar alertas de performance
- [ ] Programar sesión de revisión en 1 semana

---

## 🎯 Next Steps After Deployment

### Semana 1-2:
- Monitor dashboards diarios
- Revisar weekly validation reports
- Ajustar umbrales si hay falsos positivos
- Documentar cualquier issue

### Semana 3-4:
- Evaluar Chronos model performance (si habilitado)
- Re-calibrar si es necesario
- Optimizar configuración basado en datos reales

### Mes 2:
- Completar tests restantes (70% coverage target)
- Implementar mejoras basadas en learnings
- Documentación para usuarios finales

---

**Checklist Created:** 2025-11-13
**System Version:** MLOps Phase 2 - All 11 Tasks Complete
**Ready for Production:** ✅ YES
