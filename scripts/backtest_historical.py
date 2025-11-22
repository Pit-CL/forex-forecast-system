#!/usr/bin/env python3
"""
Backtesting Retroactivo - USD/CLP Forecast System

Genera forecasts sint éticos usando modelos ElasticNet actuales
y los compara contra datos reales históricos para obtener métricas
de accuracy reales.

Uses EXACT same feature engineering as generate_real_forecasts.py

Author: Senior Developer
Date: 2025-11-20
"""

import sys
import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Paths
BASE_PATH = Path("/opt/forex-forecast-system")
DATA_PATH = BASE_PATH / "data" / "raw" / "yahoo_finance_data.csv"
MODELS_PATH = BASE_PATH / "models" / "trained"
OUTPUT_PATH = BASE_PATH / "backtest" / "metrics.json"

# Horizons to backtest
HORIZONS = {
    "7d": 7,
    "15d": 15,
    "30d": 30,
    "90d": 90
}

def load_historical_data() -> pd.DataFrame:
    """Load historical USD/CLP data"""
    print(f"📥 Loading historical data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df = df.sort_index()
    print(f"  ✓ Loaded {len(df)} records (from {df.index[0]} to {df.index[-1]})")
    return df

def compute_features(df: pd.DataFrame, feature_names: list) -> pd.DataFrame:
    """
    Compute features needed by the model (SAME as generate_real_forecasts.py)

    Features include:
    - USDCLP lags (1, 2, 3, 5, 7, 10, 14)
    - USDCLP moving averages (5, 10, 20, 30)
    - USDCLP standard deviations (5, 10, 20, 30)
    - Ratios (USDCLP/DXY, USDCLP/Copper, Copper/Oil)
    - DXY lags (1, 2, 3, 5, 7, 10, 14)
    - DXY returns (14-day)
    - External features (SP500, Oil, VIX)
    """
    features_df = pd.DataFrame(index=df.index)

    # USDCLP features
    for lag in [1, 2, 3, 5, 7, 10, 14]:
        features_df[f'USDCLP_lag_{lag}'] = df['USDCLP'].shift(lag)

    for window in [5, 10, 20, 30]:
        features_df[f'USDCLP_ma_{window}'] = df['USDCLP'].rolling(window).mean()
        features_df[f'USDCLP_std_{window}'] = df['USDCLP'].rolling(window).std()

    # Ratios
    features_df['USDCLP_DXY_ratio'] = df['USDCLP'] / df['DXY']
    features_df['USDCLP_Copper_ratio'] = df['USDCLP'] / df['Copper']
    features_df['Copper_Oil_ratio'] = df['Copper'] / df['Oil']

    # Copper features
    for lag in [1, 2, 3, 5, 7, 10, 14]:
        features_df[f'Copper_lag_{lag}'] = df['Copper'].shift(lag)

    for window in [5, 10, 20, 30]:
        features_df[f'Copper_ma_{window}'] = df['Copper'].rolling(window).mean()
        features_df[f'Copper_std_{window}'] = df['Copper'].rolling(window).std()

    # DXY features
    for lag in [1, 2, 3, 5, 7, 10, 14]:
        features_df[f'DXY_lag_{lag}'] = df['DXY'].shift(lag)

    features_df['DXY_return_14'] = df['DXY'].pct_change(14, fill_method=None)

    # USDCLP rate of change
    features_df['USDCLP_roc_5'] = df['USDCLP'].pct_change(5, fill_method=None)
    features_df['USDCLP_roc_10'] = df['USDCLP'].pct_change(10, fill_method=None)

    # External features
    features_df['SP500'] = df['SP500']
    features_df['Oil'] = df['Oil']
    features_df['VIX'] = df['VIX']
    features_df['DXY'] = df['DXY']
    features_df['Copper'] = df['Copper']

    return features_df[feature_names]

def load_elasticnet_model(horizon: str) -> Tuple[object, object, list, Dict]:
    """Load ElasticNet model for specific horizon"""
    horizon_upper = horizon.upper()
    model_path = MODELS_PATH / horizon_upper / "elasticnet_backup.joblib"

    if not model_path.exists():
        print(f"  ✗ Model not found: {model_path}")
        return None, None, None, {}

    model_dict = joblib.load(model_path)
    model = model_dict.get('model')
    scaler = model_dict.get('scaler')
    feature_names = model_dict.get('features', [])

    print(f"  ✓ Loaded {horizon_upper} ElasticNet model ({len(feature_names)} features)")
    return model, scaler, feature_names, model_dict

def calculate_directional_accuracy(actual: List[float], predicted: List[float], current: List[float]) -> float:
    """Calculate directional accuracy (% correct direction predictions)"""
    correct = 0
    total = 0

    for a, p, c in zip(actual, predicted, current):
        actual_direction = 1 if a > c else -1
        predicted_direction = 1 if p > c else -1

        if actual_direction == predicted_direction:
            correct += 1
        total += 1

    return (correct / total * 100) if total > 0 else 0.0

def backtest_horizon(df: pd.DataFrame, horizon_key: str, horizon_days: int) -> Dict:
    """Backtest a specific horizon"""
    print(f"\n🔬 Backtesting {horizon_key.upper()} ({horizon_days} days)")

    # Load model
    model, scaler, feature_names, model_dict = load_elasticnet_model(horizon_key)

    if model is None:
        print(f"  ✗ Skipping {horizon_key} - model not found")
        return None

    # Compute features for ALL historical data
    features_df = compute_features(df, feature_names)

    # Walk-forward backtest
    actuals = []
    predictions = []
    current_prices = []

    # Use adaptive window: start from earliest date that allows testing this horizon
    # For 90D horizon: need at least 90 days of future data, so go back as far as possible
    end_date = df.index[-1]
    
    # Calculate how far back we can go (need horizon_days of future data)
    # Use maximum of 365 days or all available data
    max_lookback = min(365, len(df) - horizon_days - 30)  # Keep 30 days buffer for features
    start_date = end_date - timedelta(days=max_lookback)

    backtest_dates = df[(df.index >= start_date) & (df.index <= end_date - timedelta(days=horizon_days))].index

    print(f"  📊 Testing {len(backtest_dates)} observations from {backtest_dates[0]} to {backtest_dates[-1]}")

    debug_count = 0
    for test_date in backtest_dates:
        try:
            # Get features for test_date
            if test_date not in features_df.index:
                continue

            X = features_df.loc[test_date:test_date].values

            # Skip if any NaN
            if np.any(np.isnan(X)):
                continue

            # Get current price
            current_price = df.loc[test_date, 'USDCLP']

            # Scale features before prediction (CRITICAL!)
            X_scaled = scaler.transform(X)

            # Make prediction
            prediction = model.predict(X_scaled)[0]

            # Debug: print first 3 predictions
            if debug_count < 3:
                print(f"    Debug #{debug_count+1}: Date={test_date.date()}, Current={current_price:.2f}, Pred={prediction:.2f}")
                debug_count += 1

            # Get actual value horizon_days in the future
            future_date = test_date + timedelta(days=horizon_days)

            # Find closest available date
            future_idx = df.index.searchsorted(future_date)

            if future_idx < len(df):
                actual_price = df.iloc[future_idx]['USDCLP']

                # Skip if actual is NaN
                if np.isnan(actual_price):
                    continue

                actuals.append(actual_price)
                predictions.append(prediction)
                current_prices.append(current_price)

        except Exception as e:
            continue

    if len(actuals) < 5:
        print(f"  ✗ Not enough observations ({len(actuals)}) for {horizon_key}")
        return None

    # Calculate metrics
    actuals = np.array(actuals)
    predictions = np.array(predictions)
    current_prices = np.array(current_prices)

    # Debug: check for NaN
    print(f"  🔍 Debug: Actuals has NaN? {np.any(np.isnan(actuals))}")
    print(f"  🔍 Debug: Predictions has NaN? {np.any(np.isnan(predictions))}")
    print(f"  🔍 Debug: First 3 actuals: {actuals[:3]}")
    print(f"  🔍 Debug: First 3 predictions: {predictions[:3]}")

    mae = np.mean(np.abs(actuals - predictions))
    rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
    directional_accuracy = calculate_directional_accuracy(actuals.tolist(), predictions.tolist(), current_prices.tolist())

    print(f"  ✅ Results ({len(actuals)} samples):")
    print(f"     MAE: {mae:.2f}")
    print(f"     RMSE: {rmse:.2f}")
    print(f"     MAPE: {mape:.2f}%")
    print(f"     Directional Accuracy: {directional_accuracy:.1f}%")

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2),
        "directional_accuracy": round(directional_accuracy, 1),
        "sample_size": len(actuals)
    }

def main():
    print("=" * 80)
    print("BACKTESTING RETROACTIVO - USD/CLP ELASTICNET MODELS")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load data
    df = load_historical_data()

    # Backtest each horizon
    results = {}
    total_samples = 0

    for horizon_key, horizon_days in HORIZONS.items():
        metrics = backtest_horizon(df, horizon_key, horizon_days)

        if metrics:
            results[horizon_key] = metrics
            total_samples += metrics['sample_size']

    # Save results
    output = {
        "last_updated": datetime.now().isoformat(),
        "sample_size": total_samples,
        "horizons": results,
        "note": "Real backtesting metrics from historical walk-forward validation"
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"✅ BACKTESTING COMPLETED")
    print(f"{'=' * 80}")
    print(f"Total samples tested: {total_samples}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
