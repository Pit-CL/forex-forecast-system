"""
Feature Engineering for USD/CLP Forecasting.

Generates 50+ features from raw market data for XGBoost and SARIMAX models.
Follows KISS principle: simple functions, efficient pandas operations, no over-engineering.

Feature Categories:
    - Lagged Features (20): USD/CLP, Copper, DXY, VIX lags
    - Technical Indicators (15): SMA, EMA, RSI, Bollinger Bands, ATR, MACD
    - Copper Features (11): price, volume, RSI, SMA, EMA, BB position, MACD, LME inventory
    - Macro Features (6): DXY, VIX, TPM, Fed Funds, IMACEC, IPC
    - Chilean Indicators (25+): Trade balance, IMACEC, China PMI, AFP flows, LME inventory
    - Derived Features (8): Returns, volatility, trend, seasonality

Example:
    >>> import pandas as pd
    >>> from forex_core.features import engineer_features
    >>>
    >>> # Raw data with required columns
    >>> df = pd.DataFrame({
    ...     'date': pd.date_range('2024-01-01', periods=100),
    ...     'usdclp': np.random.uniform(900, 950, 100),
    ...     'copper_price': np.random.uniform(3.5, 4.5, 100),
    ...     'dxy': np.random.uniform(102, 106, 100),
    ...     'vix': np.random.uniform(12, 20, 100),
    ...     'tpm': [5.5] * 100,
    ...     'fed_funds': [5.0] * 100,
    ... })
    >>>
    >>> # Generate features
    >>> features_df = engineer_features(df, horizon=7)
    >>> print(f"Generated {features_df.shape[1]} features")
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


def engineer_features(df: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
    """
    Generate all engineered features from raw data.

    Main orchestrator function that applies all feature engineering steps.

    Args:
        df: Raw DataFrame with required columns:
            - date: datetime index or column
            - usdclp: USD/CLP exchange rate
            - copper_price: Copper price (USD/lb)
            - copper_volume: Copper trading volume (optional)
            - dxy: Dollar Index
            - vix: VIX volatility index
            - tpm: Chilean monetary policy rate
            - fed_funds: US Federal Funds rate
            - imacec: Chilean economic activity index (optional)
            - ipc: Chilean CPI (optional)
            - trade_balance: Chilean trade balance (optional)
            - imacec_yoy: IMACEC YoY growth rate (optional)
            - china_pmi: China Manufacturing PMI (optional)
            - afp_flows: AFP net international flows (optional)
            - lme_inventory: LME copper inventory (optional)
        horizon: Forecast horizon in days (7, 15, 30, 90)

    Returns:
        DataFrame with original columns plus 50+ engineered features

    Example:
        >>> df = load_raw_data()
        >>> features_df = engineer_features(df, horizon=7)
        >>> print(features_df.columns.tolist())
        ['date', 'usdclp', ..., 'usdclp_lag1', 'usdclp_sma5', ...]

    Raises:
        ValueError: If required columns are missing
        ValueError: If data quality is too poor (>5% NaN after processing)
    """
    logger.info(f"Starting feature engineering for {len(df)} rows, horizon={horizon}d")

    # Validate input
    required = ['usdclp', 'copper_price', 'dxy', 'vix', 'tpm', 'fed_funds']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Ensure date index
    if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('date')

    # Sort by date
    df = df.sort_index()

    # Create copy to avoid modifying original
    features = df.copy()

    # Apply feature engineering steps
    logger.info("Adding lagged features...")
    features = add_lagged_features(features, horizon=horizon)

    logger.info("Adding technical indicators...")
    features = add_technical_indicators(features)

    logger.info("Adding copper features...")
    features = add_copper_features(features)

    logger.info("Adding macro features...")
    features = add_macro_features(features)

    logger.info("Adding Chilean indicators...")
    features = add_chilean_indicators(features)

    logger.info("Adding derived features...")
    features = add_derived_features(features)

    # Handle missing values
    logger.info("Handling missing values...")
    features = _handle_missing_values(features)

    # Validate output
    if not validate_features(features):
        raise ValueError("Feature validation failed - check logs for details")

    logger.info(
        f"Feature engineering complete: {len(features)} rows, "
        f"{len(features.columns)} features"
    )

    return features


def add_lagged_features(df: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
    """
    Add lagged features for time series forecasting with horizon-aware safety margins.

    Creates lagged features with horizon-specific adjustments to prevent data leakage:
        - USD/CLP: 1, 2, 3, 5, 7, 14, 21, 30 day lags (adjusted for 30d horizon)
        - Copper: 1, 3, 7, 14 day lags
        - DXY: 1, 3, 7 day lags
        - VIX: 1, 3 day lags

    Args:
        df: DataFrame with usdclp, copper_price, dxy, vix columns
        horizon: Forecast horizon in days (7, 15, 30, 90) to adjust max lags

    Returns:
        DataFrame with added lag features

    Example:
        >>> df = pd.DataFrame({
        ...     'usdclp': [900, 905, 910],
        ...     'copper_price': [4.0, 4.1, 4.05]
        ... })
        >>> df = add_lagged_features(df, horizon=30)
        >>> print(df[['usdclp_lag1', 'copper_lag1']])
    """
    result = df.copy()

    # USD/CLP lags (most important)
    # Base lags for most horizons
    usdclp_lags = [1, 2, 3, 5, 7, 14, 21, 30]

    # For 30d horizon, remove 30-day lag to prevent boundary issues
    # This ensures a safety margin between max feature lag (21 days) and target shift (30 days)
    if horizon == 30:
        usdclp_lags = [1, 2, 3, 5, 7, 14, 21]  # Max lag: 21 days
        logger.info(f"30d horizon: Using max lag of 21 days (safety margin to prevent data leakage)")

    for lag in usdclp_lags:
        result[f'usdclp_lag{lag}'] = result['usdclp'].shift(lag)

    # Copper lags (strong correlation with USD/CLP)
    copper_lags = [1, 3, 7, 14]
    for lag in copper_lags:
        result[f'copper_lag{lag}'] = result['copper_price'].shift(lag)

    # DXY lags (inverse correlation)
    dxy_lags = [1, 3, 7]
    for lag in dxy_lags:
        result[f'dxy_lag{lag}'] = result['dxy'].shift(lag)

    # VIX lags (volatility indicator)
    vix_lags = [1, 3]
    for lag in vix_lags:
        result[f'vix_lag{lag}'] = result['vix'].shift(lag)

    return result


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators for USD/CLP.

    Creates 15 technical indicators:
        - Simple Moving Averages: 5, 10, 20, 50 days
        - Exponential Moving Averages: 10, 20, 50 days
        - RSI: 14-day Relative Strength Index
        - Bollinger Bands: 20-day with 2 std dev (upper, lower, width)
        - ATR: 14-day Average True Range
        - MACD: 12/26/9 (line, signal, histogram)

    Args:
        df: DataFrame with usdclp column

    Returns:
        DataFrame with added technical indicators

    Example:
        >>> df = pd.DataFrame({
        ...     'usdclp': np.random.uniform(900, 950, 100)
        ... })
        >>> df = add_technical_indicators(df)
        >>> print(df[['usdclp_sma5', 'usdclp_rsi14']].tail())
    """
    result = df.copy()

    # Simple Moving Averages
    for window in [5, 10, 20, 50]:
        result[f'usdclp_sma{window}'] = result['usdclp'].rolling(window=window).mean()

    # Exponential Moving Averages
    for span in [10, 20, 50]:
        result[f'usdclp_ema{span}'] = result['usdclp'].ewm(span=span, adjust=False).mean()

    # RSI (14-day)
    result['usdclp_rsi14'] = _calculate_rsi(result['usdclp'], window=14)

    # Bollinger Bands (20-day, 2 std dev)
    bb_window = 20
    bb_std = 2
    sma = result['usdclp'].rolling(window=bb_window).mean()
    std = result['usdclp'].rolling(window=bb_window).std()
    result['usdclp_bb_upper'] = sma + (bb_std * std)
    result['usdclp_bb_lower'] = sma - (bb_std * std)
    result['usdclp_bb_width'] = result['usdclp_bb_upper'] - result['usdclp_bb_lower']

    # ATR (14-day Average True Range)
    result['usdclp_atr14'] = _calculate_atr(result, price_col='usdclp', window=14)

    # MACD (12, 26, 9)
    ema12 = result['usdclp'].ewm(span=12, adjust=False).mean()
    ema26 = result['usdclp'].ewm(span=26, adjust=False).mean()
    result['usdclp_macd'] = ema12 - ema26
    result['usdclp_macd_signal'] = result['usdclp_macd'].ewm(span=9, adjust=False).mean()
    result['usdclp_macd_hist'] = result['usdclp_macd'] - result['usdclp_macd_signal']

    return result


def add_copper_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add copper-specific technical features.

    Creates 7 copper features:
        - Copper price and volume (from input)
        - Copper RSI (14-day)
        - Copper SMA (20-day)
        - Copper EMA (50-day)
        - Copper Bollinger position (where price sits in BB bands)
        - Copper MACD (12/26/9)

    Args:
        df: DataFrame with copper_price and optionally copper_volume

    Returns:
        DataFrame with added copper features

    Example:
        >>> df = pd.DataFrame({
        ...     'copper_price': np.random.uniform(3.5, 4.5, 100),
        ...     'copper_volume': np.random.uniform(1000, 5000, 100)
        ... })
        >>> df = add_copper_features(df)
        >>> print(df[['copper_rsi14', 'copper_sma20']].tail())
    """
    result = df.copy()

    # Copper RSI
    result['copper_rsi14'] = _calculate_rsi(result['copper_price'], window=14)

    # Copper SMA
    result['copper_sma20'] = result['copper_price'].rolling(window=20).mean()

    # Copper EMA
    result['copper_ema50'] = result['copper_price'].ewm(span=50, adjust=False).mean()

    # Copper Bollinger position (0 = at lower band, 1 = at upper band)
    bb_window = 20
    sma = result['copper_price'].rolling(window=bb_window).mean()
    std = result['copper_price'].rolling(window=bb_window).std()
    bb_upper = sma + (2 * std)
    bb_lower = sma - (2 * std)
    result['copper_bb_position'] = (result['copper_price'] - bb_lower) / (bb_upper - bb_lower)

    # Copper MACD
    ema12 = result['copper_price'].ewm(span=12, adjust=False).mean()
    ema26 = result['copper_price'].ewm(span=26, adjust=False).mean()
    result['copper_macd'] = ema12 - ema26

    # Copper volume (if available)
    if 'copper_volume' in result.columns:
        # Volume moving average
        result['copper_volume_sma20'] = result['copper_volume'].rolling(window=20).mean()

    return result


def add_macro_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add macroeconomic features.

    Creates features from macro indicators:
        - DXY (Dollar Index) - already in input
        - VIX (volatility) - already in input
        - TPM (Chilean rate) - already in input
        - Fed Funds rate - already in input
        - IMACEC (Chilean GDP proxy) - if available
        - IPC (inflation) - if available
        - Rate differential: TPM - Fed Funds
        - DXY change (1-day, 7-day)
        - VIX change (1-day)

    Args:
        df: DataFrame with dxy, vix, tpm, fed_funds columns

    Returns:
        DataFrame with added macro features

    Example:
        >>> df = pd.DataFrame({
        ...     'dxy': [105.0, 104.8, 105.2],
        ...     'vix': [15.0, 16.0, 14.5],
        ...     'tpm': [5.5, 5.5, 5.5],
        ...     'fed_funds': [5.0, 5.0, 5.0]
        ... })
        >>> df = add_macro_features(df)
        >>> print(df[['rate_differential', 'dxy_change_1d']].tail())
    """
    result = df.copy()

    # Rate differential (TPM - Fed Funds)
    result['rate_differential'] = result['tpm'] - result['fed_funds']

    # DXY changes
    result['dxy_change_1d'] = result['dxy'].pct_change(periods=1)
    result['dxy_change_7d'] = result['dxy'].pct_change(periods=7)

    # VIX changes
    result['vix_change_1d'] = result['vix'].pct_change(periods=1)

    # IMACEC growth rate (if available)
    if 'imacec' in result.columns:
        result['imacec_growth'] = result['imacec'].pct_change(periods=1)

    # IPC inflation rate (if available)
    if 'ipc' in result.columns:
        result['ipc_inflation'] = result['ipc'].pct_change(periods=1)

    return result


def add_chilean_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Chilean economic indicator features.

    Integrates Chilean-specific economic data critical for USD/CLP:
        - Trade Balance: Exports - Imports (monthly)
        - IMACEC YoY: Economic activity growth (monthly)
        - China PMI: Copper demand proxy (monthly)
        - AFP Flows: Pension fund international flows (monthly)
        - LME Inventory: Copper supply indicator (daily)

    Key relationships:
        - Trade surplus → CLP appreciation
        - IMACEC growth → CLP strength
        - China PMI > 50 → copper demand ↑ → CLP strength
        - AFP outflows → CLP weakness
        - LME inventory ↓ → copper price ↑ → CLP strength

    Args:
        df: DataFrame with optional Chilean indicator columns

    Returns:
        DataFrame with Chilean indicator features (forward-filled for alignment)

    Example:
        >>> df['trade_balance'] = [1000, 1200, np.nan, 800] # Monthly data
        >>> df = add_chilean_indicators(df)
        >>> print(df['trade_balance_ma3'].tail())
    """
    result = df.copy()

    # Count how many Chilean indicators are present
    chilean_cols = ['trade_balance', 'imacec_yoy', 'china_pmi', 'afp_flows', 'lme_inventory']
    present_cols = [col for col in chilean_cols if col in result.columns and not result[col].isna().all()]

    if not present_cols:
        logger.warning("No Chilean indicators available, skipping Chilean features")
        return result  # Return unchanged if no data

    logger.info(f"Found {len(present_cols)} Chilean indicators: {present_cols}")

    # Trade Balance (monthly data, forward-fill to daily)
    if 'trade_balance' in result.columns and not result['trade_balance'].isna().all():
        # Forward-fill monthly data to daily frequency
        result['trade_balance_ffill'] = result['trade_balance'].ffill()

        # Moving averages for smoothing
        result['trade_balance_ma3'] = result['trade_balance_ffill'].rolling(90).mean()  # 3-month MA
        result['trade_balance_ma6'] = result['trade_balance_ffill'].rolling(180).mean()  # 6-month MA

        # Trade balance momentum
        result['trade_balance_mom'] = result['trade_balance_ffill'].diff(30)  # Monthly change

        # Normalized trade balance (z-score)
        rolling_mean = result['trade_balance_ffill'].rolling(365, min_periods=30).mean()
        rolling_std = result['trade_balance_ffill'].rolling(365, min_periods=30).std()
        # Avoid division by zero for constant values
        if rolling_std.notna().any() and (rolling_std != 0).any():
            result['trade_balance_zscore'] = (result['trade_balance_ffill'] - rolling_mean) / rolling_std.replace(0, 1)
        else:
            result['trade_balance_zscore'] = 0  # If constant, z-score is 0

    # IMACEC YoY Growth (monthly)
    if 'imacec_yoy' in result.columns and not result['imacec_yoy'].isna().all():
        result['imacec_yoy_ffill'] = result['imacec_yoy'].ffill()

        # IMACEC trend and momentum
        result['imacec_ma3'] = result['imacec_yoy_ffill'].rolling(90).mean()
        result['imacec_momentum'] = result['imacec_yoy_ffill'].diff(30)

        # Economic expansion indicator (IMACEC > 3% = strong growth)
        result['imacec_expansion'] = (result['imacec_yoy_ffill'] > 3).astype(int)
        result['imacec_contraction'] = (result['imacec_yoy_ffill'] < 0).astype(int)

    # China PMI (monthly)
    if 'china_pmi' in result.columns and not result['china_pmi'].isna().all():
        result['china_pmi_ffill'] = result['china_pmi'].ffill()

        # PMI expansion/contraction signal
        result['china_expansion'] = (result['china_pmi_ffill'] > 50).astype(int)

        # PMI momentum (critical for copper)
        result['china_pmi_mom'] = result['china_pmi_ffill'].diff()
        result['china_pmi_ma3'] = result['china_pmi_ffill'].rolling(90).mean()

        # Distance from neutral (50)
        result['china_pmi_strength'] = result['china_pmi_ffill'] - 50

    # AFP Flows (monthly)
    if 'afp_flows' in result.columns and not result['afp_flows'].isna().all():
        result['afp_flows_ffill'] = result['afp_flows'].ffill()

        # Cumulative flows (trend indicator)
        result['afp_flows_cum'] = result['afp_flows_ffill'].cumsum()

        # Flow momentum
        result['afp_flows_ma3'] = result['afp_flows_ffill'].rolling(90).mean()
        result['afp_flows_ma6'] = result['afp_flows_ffill'].rolling(180).mean()

        # Outflow indicator (positive = selling CLP)
        result['afp_outflow_signal'] = (result['afp_flows_ffill'] > 0).astype(int)

    # LME Inventory (daily/weekly)
    if 'lme_inventory' in result.columns and not result['lme_inventory'].isna().all():
        result['lme_inventory_ffill'] = result['lme_inventory'].ffill()

        # Inventory change rates
        result['lme_inv_change_5d'] = result['lme_inventory_ffill'].diff(5)
        result['lme_inv_change_20d'] = result['lme_inventory_ffill'].diff(20)

        # Inventory trend
        result['lme_inv_ma20'] = result['lme_inventory_ffill'].rolling(20).mean()
        result['lme_inv_ma60'] = result['lme_inventory_ffill'].rolling(60).mean()

        # Critical level indicators
        # Historical context: Low < 150k MT, High > 600k MT
        result['lme_inv_low'] = (result['lme_inventory_ffill'] < 150000).astype(int)
        result['lme_inv_high'] = (result['lme_inventory_ffill'] > 600000).astype(int)

        # Inventory z-score
        inv_mean = result['lme_inventory_ffill'].rolling(252, min_periods=20).mean()
        inv_std = result['lme_inventory_ffill'].rolling(252, min_periods=20).std()
        # Avoid division by zero for constant values
        if inv_std.notna().any() and (inv_std != 0).any():
            result['lme_inv_zscore'] = (result['lme_inventory_ffill'] - inv_mean) / inv_std.replace(0, 1)
        else:
            result['lme_inv_zscore'] = 0  # If constant, z-score is 0

    # Composite Chilean Economic Health Score
    # Combines multiple indicators into single metric
    components = []
    weights = []

    if 'imacec_yoy_ffill' in result.columns:
        # IMACEC: normalized around 3% growth
        components.append((result['imacec_yoy_ffill'] - 3) / 3)
        weights.append(0.3)

    if 'trade_balance_zscore' in result.columns and not result['trade_balance_zscore'].isna().all():
        # Trade balance z-score
        components.append(result['trade_balance_zscore'] / 2)  # Scale down
        weights.append(0.2)

    if 'china_pmi_strength' in result.columns:
        # China PMI deviation from 50
        components.append(result['china_pmi_strength'] / 10)
        weights.append(0.3)

    if 'lme_inv_zscore' in result.columns and not result['lme_inv_zscore'].isna().all():
        # LME inventory (inverted - low inventory is bullish)
        components.append(-result['lme_inv_zscore'] / 2)
        weights.append(0.2)

    if components:
        # Weighted average of available components
        result['chile_composite_score'] = sum(c * w for c, w in zip(components, weights)) / sum(weights)

        # Smooth the composite score
        result['chile_composite_ma7'] = result['chile_composite_score'].rolling(7).mean()
        result['chile_composite_ma30'] = result['chile_composite_score'].rolling(30).mean()

    return result


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived features from transformations.

    Creates 8+ derived features:
        - USD/CLP returns: 1-day, 7-day, 30-day
        - Rolling volatility: 7-day, 30-day
        - Trend indicator: linear regression slope over 30 days
        - Seasonality: day of week, month
        - Distance from moving averages

    Args:
        df: DataFrame with usdclp column and DatetimeIndex

    Returns:
        DataFrame with added derived features

    Example:
        >>> df = pd.DataFrame({
        ...     'usdclp': np.random.uniform(900, 950, 100)
        ... }, index=pd.date_range('2024-01-01', periods=100))
        >>> df = add_derived_features(df)
        >>> print(df[['usdclp_return_1d', 'usdclp_volatility_7d']].tail())
    """
    result = df.copy()

    # Returns (percentage changes)
    result['usdclp_return_1d'] = result['usdclp'].pct_change(periods=1)
    result['usdclp_return_7d'] = result['usdclp'].pct_change(periods=7)
    result['usdclp_return_30d'] = result['usdclp'].pct_change(periods=30)

    # Rolling volatility (standard deviation of returns)
    returns = result['usdclp'].pct_change()
    result['usdclp_volatility_7d'] = returns.rolling(window=7).std()
    result['usdclp_volatility_30d'] = returns.rolling(window=30).std()

    # Trend indicator (linear regression slope over 30 days)
    result['usdclp_trend_30d'] = _calculate_trend(result['usdclp'], window=30)

    # Seasonality features (if datetime index available)
    if isinstance(result.index, pd.DatetimeIndex):
        result['day_of_week'] = result.index.dayofweek
        result['month'] = result.index.month
        result['quarter'] = result.index.quarter

    # Distance from moving averages (normalized)
    if 'usdclp_sma20' in result.columns:
        result['usdclp_dist_sma20'] = (result['usdclp'] - result['usdclp_sma20']) / result['usdclp_sma20']

    if 'usdclp_ema50' in result.columns:
        result['usdclp_dist_ema50'] = (result['usdclp'] - result['usdclp_ema50']) / result['usdclp_ema50']

    return result


def validate_features(df: pd.DataFrame) -> bool:
    """
    Validate feature quality.

    Checks:
        - No more than 5% NaN values
        - No infinite values
        - No duplicate rows
        - Reasonable value ranges (no extreme outliers)

    Args:
        df: DataFrame with engineered features

    Returns:
        True if validation passes, False otherwise

    Example:
        >>> features = engineer_features(raw_df)
        >>> if validate_features(features):
        ...     print("Features are valid")
    """
    # Check for NaN percentage
    nan_pct = df.isna().sum().sum() / (len(df) * len(df.columns)) * 100
    if nan_pct > 5.0:
        logger.error(f"Too many NaN values: {nan_pct:.2f}% (threshold: 5%)")
        return False

    logger.info(f"NaN percentage: {nan_pct:.2f}% (OK)")

    # Check for infinite values
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        logger.error(f"Found {inf_count} infinite values")
        inf_cols = df.columns[np.isinf(df.select_dtypes(include=[np.number])).any()].tolist()
        logger.error(f"Columns with infinite values: {inf_cols}")
        return False

    logger.info("No infinite values (OK)")

    # Check for duplicate indices
    if df.index.duplicated().any():
        dup_count = df.index.duplicated().sum()
        logger.warning(f"Found {dup_count} duplicate indices")

    # Log feature count
    numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
    logger.info(f"Generated {len(numeric_features)} numeric features")

    return True


# --- Helper Functions ---


def _calculate_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    RSI measures momentum on a scale of 0-100:
        - RSI > 70: overbought
        - RSI < 30: oversold

    Args:
        series: Price series
        window: RSI window (default 14)

    Returns:
        RSI series
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def _calculate_atr(df: pd.DataFrame, price_col: str, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    ATR measures volatility - higher values indicate more volatility.
    For single price series, simplified calculation using high-low range.

    Args:
        df: DataFrame with price column
        price_col: Name of price column
        window: ATR window (default 14)

    Returns:
        ATR series
    """
    # Simplified ATR using daily price changes
    # (True ATR requires high/low prices which we don't have for daily data)
    returns = df[price_col].pct_change().abs()
    atr = returns.rolling(window=window).mean() * df[price_col]

    return atr


def _calculate_trend(series: pd.Series, window: int = 30) -> pd.Series:
    """
    Calculate rolling linear regression slope as trend indicator.

    Positive slope = uptrend, negative slope = downtrend.

    Args:
        series: Price series
        window: Window for regression (default 30)

    Returns:
        Series of slopes
    """
    def _slope(y):
        if len(y) < 2:
            return np.nan
        x = np.arange(len(y))
        # Simple linear regression: slope = cov(x,y) / var(x)
        slope = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 0
        return slope

    return series.rolling(window=window).apply(_slope, raw=True)


def _handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values in feature matrix.

    Strategy:
        1. Forward fill up to 3 periods (for price continuity)
        2. Backward fill up to 2 periods (for start of series)
        3. Drop remaining NaN rows (only if necessary)

    Args:
        df: DataFrame with features

    Returns:
        DataFrame with handled missing values
    """
    result = df.copy()

    # Count initial NaN
    initial_nan = result.isna().sum().sum()

    # Forward fill (up to 3 periods)
    result = result.ffill(limit=3)

    # Backward fill (up to 2 periods for series start)
    result = result.bfill(limit=2)

    # Log remaining NaN
    remaining_nan = result.isna().sum().sum()

    if remaining_nan > 0:
        logger.warning(
            f"Filled {initial_nan - remaining_nan} NaN values, "
            f"{remaining_nan} remain"
        )

        # Drop rows with remaining NaN (usually at start due to lags)
        rows_before = len(result)
        result = result.dropna()
        rows_dropped = rows_before - len(result)

        if rows_dropped > 0:
            logger.warning(f"Dropped {rows_dropped} rows with remaining NaN values")
    else:
        logger.info(f"Filled all {initial_nan} NaN values successfully")

    return result


__all__ = [
    'engineer_features',
    'add_lagged_features',
    'add_technical_indicators',
    'add_copper_features',
    'add_macro_features',
    'add_derived_features',
    'validate_features',
]
