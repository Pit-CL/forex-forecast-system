
## [1.0.2] - 2025-11-22

### Added
- **Interest Rate Differential**: Nueva variable exógena agregada al pipeline de datos
  - Fed Funds Rate (DFF) desde FRED API - diario
  - Chile Interbank Rate (IRSTCI01CLM156N) desde FRED API - mensual
  - Cálculo automático del diferencial (Chile - USA)
  - Archivo: data/raw/fred_interest_rates.csv
  
### Changed
- scripts/collect_data.py: Agregada sección 3 para colección de datos FRED

### Technical Details
- FRED API Key configurada en collect_data.py
- Datos históricos desde 2010-01-01
- Forward-fill aplicado a tasa Chile (mensual → diaria)
- El diferencial actual es +0.87% (Chile 4.75% - USA 3.88%)

### Note
Los datos de tasas se colectan pero AÚN NO se usan en el modelo.
Próximo paso: Integrar rate_differential en feature engineering.
