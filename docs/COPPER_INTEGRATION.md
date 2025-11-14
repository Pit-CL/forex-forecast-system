# Copper Price Integration Guide

## Overview

This document describes the copper price data integration in the USD/CLP forecasting system. Copper prices are a critical input for Chilean peso forecasting as copper represents approximately 50% of Chile's exports, making the copper-CLP relationship fundamental to exchange rate dynamics.

## Architecture

### Data Sources

**Primary Source: Yahoo Finance (HG=F)**
- **Symbol:** HG=F (High Grade Copper Futures - COMEX)
- **Updates:** Daily, near real-time
- **Historical Range:** 10+ years available
- **Format:** USD per pound
- **Reliability:** High (no API key required)
- **Latency:** Low (updates within hours of market close)

**Backup Source: FRED API (PCOPPUSDM)**
- **Series ID:** PCOPPUSDM (Global Price of Copper)
- **Updates:** Monthly (slower than Yahoo)
- **Historical Range:** Extensive (1960s onwards)
- **Format:** USD per metric ton (auto-converted to USD/lb)
- **Reliability:** Very high (official Federal Reserve data)
- **Requires:** FRED_API_KEY environment variable

### Automatic Fallback Strategy

```
1. Try Yahoo Finance HG=F
   └─ Success → Use fresh data
   └─ Failure → Try FRED API
      └─ Success → Use FRED data
      └─ Failure → Try cached warehouse data
         └─ Success → Use cached data (with warning)
         └─ Failure → Use empty series (non-blocking)
```

This multi-layer fallback ensures the forecast pipeline **never fails** due to copper data unavailability, though forecast quality may degrade without copper features.

## Features Computed

### 1. Raw Price
- `copper_series`: Historical daily price series (USD/lb)

### 2. Returns
- `copper_returns_1d`: 1-day log returns
- `copper_returns_5d`: 5-day log returns (weekly momentum)
- `copper_returns_20d`: 20-day log returns (monthly momentum)

**Why log returns?**
- Stationary properties (better for time series models)
- Symmetric treatment of gains/losses
- Compounding-aware

### 3. Volatility
- `copper_volatility_20d`: 20-day annualized volatility (short-term risk)
- `copper_volatility_60d`: 60-day annualized volatility (medium-term risk)

**Formula:** `std(log_returns) * sqrt(252)`

**Interpretation:**
- Higher volatility → Higher uncertainty in copper market
- May correlate with increased USD/CLP volatility
- Typical range: 0.15 - 0.40 (15% - 40% annualized)

### 4. Trend Indicators
- `copper_sma_20`: 20-day Simple Moving Average
- `copper_sma_50`: 50-day Simple Moving Average
- `copper_trend_signal`: Trend direction signal
  - `1.0`: Uptrend (SMA20 > SMA50)
  - `-1.0`: Downtrend (SMA20 < SMA50)
  - `0.0`: Neutral (equal)

**Trading interpretation:**
- Uptrend in copper → Chile exports more valuable → CLP strengthens → USD/CLP falls
- Downtrend in copper → Chile exports less valuable → CLP weakens → USD/CLP rises

### 5. Momentum
- `copper_rsi_14`: 14-period Relative Strength Index

**Interpretation:**
- RSI > 70: Overbought (potential reversal down)
- RSI < 30: Oversold (potential reversal up)
- RSI 40-60: Neutral zone

### 6. Normalized Price
- `copper_price_normalized`: Z-score normalized over 1-year rolling window

**Use:** Standardized input for machine learning models

### 7. Correlation Tracking
- `copper_usdclp_correlation_90d`: 90-day rolling correlation with USD/CLP

**Expected relationship:**
- **Negative correlation:** Higher copper → Stronger CLP → Lower USD/CLP
- Typical range: -0.5 to -0.8
- If correlation weakens or reverses, may indicate regime change

## Implementation Files

### Core Provider
**File:** `src/forex_core/data/providers/copper_prices.py`

**Class:** `CopperPricesClient`

**Key Methods:**
```python
def fetch_series(years: int = 5, force_backup: bool = False) -> pd.Series
    """Fetch copper price series with automatic fallback."""

def get_latest_indicator(source_id: int) -> Indicator
    """Get current spot copper price as Indicator."""

def compute_features(series: pd.Series) -> Dict[str, pd.Series]
    """Compute all technical features from raw price series."""

def compute_correlation_with_usdclp(
    copper_series: pd.Series,
    usdclp_series: pd.Series,
    window: int = 90
) -> pd.Series
    """Compute rolling correlation with USD/CLP."""
```

### Integration Point
**File:** `src/forex_core/data/loader.py`

**Changes:**
1. Added `CopperPricesClient` initialization in `DataLoader.__init__()`
2. Added `copper_features` field to `DataBundle` dataclass
3. Replaced mindicador copper with Yahoo/FRED copper in `load()` method
4. Added `_load_copper_data()` method with triple-layer fallback

**Data Flow:**
```
DataLoader.load()
    └─ _load_copper_data()
        ├─ copper_client.fetch_series(years=5)
        ├─ warehouse.upsert_series("copper_hgf_usd_lb", series)
        ├─ copper_client.get_latest_indicator(source_id)
        ├─ copper_client.compute_features(series)
        └─ copper_client.compute_correlation_with_usdclp(...)
```

## Usage Examples

### Standalone Usage

```python
from forex_core.config import get_settings
from forex_core.data.providers import CopperPricesClient

settings = get_settings()
client = CopperPricesClient(settings)

# Fetch 5 years of data
series = client.fetch_series(years=5)
print(f"Latest copper price: ${series.iloc[-1]:.2f} USD/lb")

# Compute features
features = client.compute_features(series)
print(f"20-day volatility: {features['copper_volatility_20d'].iloc[-1]:.2%}")
print(f"RSI: {features['copper_rsi_14'].iloc[-1]:.1f}")
```

### Via DataLoader (Production)

```python
from forex_core.config import get_settings
from forex_core.data import DataLoader

settings = get_settings()
loader = DataLoader(settings)

# Load all data including copper
bundle = loader.load()

# Access copper data
print(f"Copper spot: ${bundle.indicators['copper'].value:.2f}")
print(f"Copper series: {len(bundle.copper_series)} days")

if bundle.copper_features:
    vol = bundle.copper_features['copper_volatility_20d'].iloc[-1]
    rsi = bundle.copper_features['copper_rsi_14'].iloc[-1]
    corr = bundle.copper_features['copper_usdclp_correlation_90d'].iloc[-1]

    print(f"Volatility (20d): {vol:.2%}")
    print(f"RSI: {rsi:.1f}")
    print(f"Copper-USDCLP Correlation: {corr:.3f}")
```

### Accessing in Forecast Models

```python
# In your forecasting code
bundle = loader.load()

# Check if copper features available
if bundle.copper_features:
    # Use copper volatility as exogenous variable
    copper_vol = bundle.copper_features['copper_volatility_20d']

    # Align with USD/CLP series
    aligned_data = pd.DataFrame({
        'usdclp': bundle.usdclp_series,
        'copper_vol': copper_vol,
        'copper_returns': bundle.copper_features['copper_returns_1d']
    }).dropna()

    # Use in VAR, ARIMA-X, or ML models
    # ...
```

## Deployment Guide

### Step 1: Verify Installation

No new dependencies required! Copper integration uses existing libraries:
- `pandas`, `numpy`: Already in requirements.txt
- `httpx`: Already used by YahooClient
- FRED API: Optional (already integrated for other features)

### Step 2: Test Integration

```bash
# Run comprehensive test suite
python scripts/test_copper_integration.py
```

**Expected output:**
```
✓ PASS: CopperPricesClient Standalone
✓ PASS: DataLoader Integration
✓ PASS: FRED Fallback
TOTAL: 3/3 tests passed
✓ ALL TESTS PASSED
```

### Step 3: Optional - Enable FRED Backup

If you want the FRED fallback (recommended for production):

```bash
# Get free API key from https://fred.stlouisfed.org/docs/api/api_key.html
# Add to .env file:
echo "FRED_API_KEY=your_key_here" >> .env
```

**Note:** You likely already have `FRED_API_KEY` configured since the system uses FRED for Fed Funds rate data.

### Step 4: Deploy to Production

The copper integration is **backward compatible** and **non-breaking**:

```bash
# No changes to Docker needed - just rebuild
docker-compose build forecaster-7d
docker-compose build forecaster-15d
docker-compose build forecaster-30d
docker-compose build forecaster-90d

# Test locally first
docker-compose run forecaster-7d python -m services.forecaster_7d.cli validate

# Deploy
docker-compose up -d
```

### Step 5: Monitor Logs

After deployment, check logs for copper data loading:

```bash
docker-compose logs -f forecaster-7d | grep -i copper
```

**Expected log messages:**
```
[INFO] Loading copper prices with enhanced features
[INFO] Fetching copper prices from Yahoo Finance (HG=F, 5y)
[INFO] Successfully fetched 1258 copper price points from Yahoo (range: $2.15-$5.04)
[INFO] Computed 10 copper features (vol_20d mean: 0.234)
[INFO] Copper-USDCLP correlation (90d avg): -0.687
```

**Warning scenarios (non-blocking):**
```
[WARNING] Yahoo Finance copper fetch failed: <error>
[INFO] Using FRED backup for copper prices (PCOPPUSDM)
[INFO] Successfully fetched 348 copper price points from FRED
```

```
[WARNING] Attempting to use cached copper data from warehouse
[INFO] Using 1258 cached copper data points
```

```
[ERROR] Both Yahoo Finance and FRED copper sources failed
[WARNING] Creating empty copper series - forecasts may be degraded
```

## Error Handling

### Graceful Degradation

The system is designed to **never fail** due to copper data issues:

1. **Primary fails:** Use FRED backup
2. **FRED fails:** Use cached warehouse data
3. **Cache empty:** Use empty series with NaN values
4. **Result:** Forecast continues but with `copper_features = None`

### Impact of Missing Copper Data

- **Short-term (1-7 days):** Minimal impact (other indicators compensate)
- **Medium-term (15-30 days):** Moderate impact (copper trend matters)
- **Long-term (90+ days):** Higher impact (copper macro correlation important)

### Monitoring

Add to your monitoring dashboard:

```python
# Check copper data health in reports
if bundle.copper_features is None:
    send_alert("Copper features unavailable - using degraded forecast")

# Check data freshness
copper_age = (datetime.now() - bundle.copper_series.index[-1]).days
if copper_age > 5:
    send_alert(f"Copper data is {copper_age} days old")
```

## Performance Considerations

### Data Volume
- 5 years daily data: ~1,258 data points
- Memory footprint: ~100 KB (negligible)
- 10 derived features: ~1 MB total (negligible)

### Computation Time
- Fetch from Yahoo: 1-3 seconds
- Feature computation: <0.1 seconds
- Correlation calculation: <0.1 seconds
- **Total overhead:** ~2-4 seconds added to pipeline

### Caching
Copper data is automatically cached in warehouse (`data/warehouse/copper_hgf_usd_lb.parquet`):
- First run: Fetches fresh data (2-4 seconds)
- Subsequent runs: Uses cache if source fails (instant)
- Cache refresh: Automatic on successful fetch

## Troubleshooting

### Issue: Yahoo Finance returns 403 Forbidden

**Cause:** Yahoo Finance occasionally blocks requests

**Solution:** System automatically falls back to FRED. If persistent:
```python
# Force FRED in copper_prices.py temporarily
series = client.fetch_series(years=5, force_backup=True)
```

### Issue: FRED API rate limit exceeded

**Cause:** FRED free tier limit is 120 requests/minute

**Solution:**
- System only makes 1 FRED copper request per run
- If hitting limit, you're making >120 total FRED requests/min across all services
- Add delay between forecast runs or use cached data

### Issue: All sources fail

**Cause:** Network issues or both APIs down simultaneously

**Solution:**
1. Check logs for specific error messages
2. System will use cached data from warehouse
3. Forecast continues with degraded accuracy
4. Fix source connectivity and next run will refresh

### Issue: Copper features showing NaN values

**Cause:** Insufficient historical data (need >60 days for 60-day volatility)

**Solution:**
- Increase `years` parameter in `fetch_series()`
- Or wait for more daily data to accumulate
- Features with long windows (60d, 252d) will have NaN for initial period

## Future Enhancements

Potential improvements to consider:

1. **Additional Copper Contracts:**
   - LME Copper (London Metal Exchange)
   - Shanghai Futures Exchange copper
   - Multi-exchange arbitrage signals

2. **Inventory Data:**
   - COMEX copper inventories
   - LME warehouse stocks
   - Chilean copper production data

3. **Copper Spreads:**
   - Spot vs. futures spread (contango/backwardation)
   - Near vs. far futures (term structure)

4. **ML-Based Features:**
   - Copper price regime classification (bull/bear/ranging)
   - Anomaly detection in copper-CLP relationship
   - Predicted copper price (meta-forecast)

5. **Alternative Data:**
   - Satellite imagery of Chilean mines
   - Shipping data (copper exports)
   - Chinese demand indicators (PMI, construction)

## References

- **COMEX HG Futures:** https://www.cmegroup.com/markets/metals/base/copper.html
- **FRED Copper Data:** https://fred.stlouisfed.org/series/PCOPPUSDM
- **Chile Copper Commission:** https://www.cochilco.cl/
- **Yahoo Finance API:** Unofficial API, use at own risk (no SLA)

## Support

For issues or questions about copper integration:

1. Check logs: `docker-compose logs forecaster-7d | grep -i copper`
2. Run test suite: `python scripts/test_copper_integration.py`
3. Verify data sources are accessible: `curl -I "https://query1.finance.yahoo.com/v8/finance/chart/HG=F"`
4. Review this documentation
5. Open GitHub issue with logs and error messages

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
**Status:** Production Ready
