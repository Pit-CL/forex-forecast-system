# Instrucciones de Despliegue - Refinamiento Profesional USD/CLP

## Resumen de Mejoras Implementadas

Se han implementado 4 mejoras criticas al sistema USD/CLP basadas en su feedback:

1. **CRITICO - Fechas solapadas corregidas**
   - Dashboard Macro (4 paneles): formato "15-Nov" con rotacion 45°
   - Regimen de Riesgo (3 paneles): mismo formato limpio
   - Limitado a 5-8 ticks por grafico

2. **Justificacion del modelo agregada**
   - Seccion "Metodologia" expandida de 3 a ~30 lineas
   - Explica POR QUE se escogio ARIMA+VAR+RandomForest
   - Incluye determinacion de pesos e intervalos de confianza

3. **Explicacion de cada grafico**
   - 4 nuevas secciones de explicacion (~200 palabras c/u)
   - Que muestra, como interpretar, insight actual
   - Panel Tecnico, Correlaciones, Dashboard Macro, Regimen

4. **Atribucion de fuentes**
   - Caption en cada grafico: "Elaboracion propia con datos de [fuente]"
   - Estilo academico profesional

## Opcion 1: Despliegue Automatizado (RECOMENDADO)

```bash
# Desde su maquina local
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
./deploy_refinements.sh
```

Este script:
- Se conecta a Vultr via SSH
- Pull de los cambios desde develop
- Rebuild del container forecaster-7d
- Genera PDF de prueba
- Muestra instrucciones para descargar

## Opcion 2: Despliegue Manual

### Paso 1: Conectar a Vultr
```bash
ssh reporting
```

### Paso 2: Actualizar codigo
```bash
cd /home/deployer/forex-forecast-system
git fetch origin
git checkout develop
git pull origin develop
```

### Paso 3: Verificar cambios
```bash
git log -1 --oneline
# Deberia mostrar: "feat: professional refinement of charts and methodology"
```

### Paso 4: Rebuild container
```bash
docker compose down
docker compose build forecaster-7d
```

### Paso 5: Generar PDF de prueba
```bash
docker compose run --rm forecaster-7d python -m services.forecaster_7d.cli run --skip-email
```

### Paso 6: Verificar PDF generado
```bash
ls -lth reports/usdclp_report_7d_*.pdf | head -1
# Deberia mostrar un PDF de ~1.5 MB generado hace segundos
```

## Validacion del PDF

### Checklist de Calidad

Descargue el PDF y verifique:

1. **Fechas Legibles** (CRITICO)
   - [ ] Dashboard Macro - Panel "USD/CLP vs Cobre": fechas claras sin solapar
   - [ ] Dashboard Macro - Panel "TPM/Fed Differential": fechas claras
   - [ ] Dashboard Macro - Panel "DXY": fechas claras
   - [ ] Dashboard Macro - Panel "IPC Chile": fechas claras
   - [ ] Regimen de Riesgo - Panel DXY: fechas claras
   - [ ] Regimen de Riesgo - Panel VIX: fechas claras
   - [ ] Regimen de Riesgo - Panel EEM: fechas claras

2. **Atribucion de Fuentes**
   - [ ] Panel Tecnico: Caption "Fuente: Elaboracion propia con datos de Mindicador.cl y Alpha Vantage"
   - [ ] Matriz Correlaciones: Caption "Fuente: Elaboracion propia con datos de Yahoo Finance"
   - [ ] Dashboard Macro: Caption "Fuente: Elaboracion propia con datos de Mindicador.cl (BCCh), Yahoo Finance"
   - [ ] Regimen de Riesgo: Caption "Fuente: Elaboracion propia con datos de Yahoo Finance (DXY, VIX, EEM)"

3. **Justificacion del Modelo**
   - [ ] Seccion "Metodologia y Validacion" presente
   - [ ] Subseccion "Justificacion de la Seleccion del Modelo" con ~30 lineas
   - [ ] Explica ARIMA-GARCH, VAR, Random Forest por separado
   - [ ] Incluye "Determinacion de Pesos" y "Intervalos de Confianza"
   - [ ] Muestra pesos actuales del ensemble al final

4. **Explicaciones de Graficos**
   - [ ] Despues de "Proyeccion Cuantitativa": Explicacion "Analisis Tecnico USD/CLP (60 dias)"
   - [ ] Despues de Analisis Tecnico: Explicacion "Matriz de Correlaciones (60 dias)"
   - [ ] Antes de seccion Regimen: Explicacion "Dashboard de Drivers Macroeconomicos"
   - [ ] En seccion Regimen: Explicacion "Regimen de Riesgo de Mercado (5 dias)"

### Descarga del PDF para Revision

```bash
# Desde su maquina local
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_report_7d_*.pdf ~/Downloads/
```

O use el ultimo PDF generado:
```bash
cd ~/Downloads
ls -t usdclp_report_7d_*.pdf | head -1
open $(ls -t usdclp_report_7d_*.pdf | head -1)  # Abre en visor PDF
```

## Metricas Esperadas

| Metrica | Antes | Despues | Cambio |
|---------|-------|---------|--------|
| Tamano PDF | 1.2 MB | ~1.5 MB | +25% (mas contenido) |
| Paginas | 8-12 | 12-14 | +2-4 paginas |
| Lineas Metodologia | 3 | ~30 | +900% |
| Explicaciones graficos | 0 | 4 | Nuevo |
| Captions con fuente | 0 | 6 | Nuevo |
| Fechas legibles | No | Si | CRITICO resuelto |

## Troubleshooting

### Error: "PDF no generado"
```bash
# Ver logs completos
docker compose run --rm forecaster-7d python -m services.forecaster_7d.cli run --skip-email 2>&1 | tee deployment.log
```

### Error: "Fechas aun solapadas"
- Verificar que el commit "feat: professional refinement" este en develop
- Confirmar que se hizo rebuild del container (no solo restart)
- Revisar logs de matplotlib por warnings

### Error: "Captions no aparecen"
- Verificar version de matplotlib en container
- Confirmar que `fig.text()` se ejecuta antes de `fig.savefig()`
- Revisar que `tight_layout(rect=[...])` tenga espacio para captions

## Proximos Pasos (Si necesita mas refinamiento)

1. Ajustar espaciado entre graficos y explicaciones
2. Agregar tabla comparativa de performance de modelos
3. Incluir ejemplo numerico de calculo de pesos
4. Agregar referencias bibliograficas
5. Crear graficos adicionales (residuales, QQ-plots)

## Soporte

Si encuentra algun problema:
1. Ejecute con logs completos (comando arriba)
2. Descargue el PDF generado para inspeccion visual
3. Reporte issue con:
   - Commit hash actual (`git log -1 --oneline`)
   - Logs de ejecucion
   - Screenshot del problema (si es visual)

---

**Implementado**: 2025-11-12
**Agent**: Claude Code (Sonnet 4.5)
**Archivos modificados**: charting.py (+63), builder.py (+186), docs (+154)
**Commit**: 7eab686 "feat: professional refinement of charts and methodology"
