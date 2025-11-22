"""
Optimized ML Training Script with Outlier Filtering and Robust Validation
Version 3.0 - Production Ready
"""
import pandas as pd
import numpy as np
from pathlib import Path
import lightgbm as lgb
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import joblib
import warnings
warnings.filterwarnings('ignore')

# Paths
BASE_DIR = Path("/opt/forex-forecast-system")
DATA_PATH = BASE_DIR / "data" / "raw" / "yahoo_finance_data.csv"
MODELS_DIR = BASE_DIR / "models" / "trained"

# Horizons to train
HORIZONS = {
    '7D': 7,
    '15D': 15,
    '30D': 30,
    '90D': 90
}

def clean_data_remove_outliers(df, target_col='USDCLP', max_daily_change=0.03):
    """Remove extreme outliers from training data"""
    print(f"Original data shape: {df.shape}")

    # Calculate daily returns
    returns = df[target_col].pct_change(fill_method=None)

    # Filter out extreme daily changes (> 3%)
    extreme_mask = returns.abs() > max_daily_change
    extreme_count = extreme_mask.sum()

    if extreme_count > 0:
        print(f"Removing {extreme_count} extreme outliers (>{max_daily_change*100}% daily change)")
        # Keep only non-extreme values
        df_clean = df[~extreme_mask].copy()
    else:
        df_clean = df.copy()

    print(f"Cleaned data shape: {df_clean.shape}")
    return df_clean

def create_features_enhanced(data, target_col='USDCLP'):
    """Enhanced feature engineering with technical indicators"""
    df_feat = data.copy()

    # 1. LAG FEATURES
    for lag in [1, 2, 3, 5, 7, 10, 14]:
        df_feat[f'{target_col}_lag_{lag}'] = df_feat[target_col].shift(lag)
        if 'Copper' in df_feat.columns:
            df_feat[f'Copper_lag_{lag}'] = df_feat['Copper'].shift(lag)
        if 'DXY' in df_feat.columns:
            df_feat[f'DXY_lag_{lag}'] = df_feat['DXY'].shift(lag)

    # 2. ROLLING STATISTICS
    for window in [5, 10, 20, 30]:
        df_feat[f'{target_col}_ma_{window}'] = df_feat[target_col].rolling(window).mean()
        df_feat[f'{target_col}_std_{window}'] = df_feat[target_col].rolling(window).std()
        if 'Copper' in df_feat.columns:
            df_feat[f'Copper_ma_{window}'] = df_feat['Copper'].rolling(window).mean()

    # 3. CROSS-MARKET FEATURES
    if 'Copper' in df_feat.columns:
        df_feat['USDCLP_Copper_ratio'] = df_feat[target_col] / df_feat['Copper']
    if 'DXY' in df_feat.columns:
        df_feat['USDCLP_DXY_ratio'] = df_feat[target_col] / df_feat['DXY']
    if 'Copper' in df_feat.columns and 'Oil' in df_feat.columns:
        df_feat['Copper_Oil_ratio'] = df_feat['Copper'] / df_feat['Oil']

    # 4. RETURN FEATURES (percentage change)
    if 'DXY' in df_feat.columns:
        df_feat['DXY_return_14'] = df_feat['DXY'].pct_change(periods=14, fill_method=None)

    # 5. MOMENTUM INDICATORS
    # Rate of Change (ROC)
    df_feat[f'{target_col}_roc_5'] = df_feat[target_col].pct_change(periods=5, fill_method=None)
    df_feat[f'{target_col}_roc_10'] = df_feat[target_col].pct_change(periods=10, fill_method=None)

    return df_feat

def prepare_data_for_horizon(df, horizon_days, target_col='USDCLP'):
    """Prepare features and target for specific horizon"""
    # Create features
    df_with_features = create_features_enhanced(df, target_col)

    # Create target: price N days ahead
    df_with_features['target'] = df_with_features[target_col].shift(-horizon_days)

    # Drop NaN values
    df_clean = df_with_features.dropna()

    # Separate features and target
    exclude_cols = [target_col, 'target', 'Copper', 'Oil', 'DXY', 'SP500', 'VIX']
    feature_cols = [col for col in df_clean.columns if col not in exclude_cols]

    # Keep raw market data as features
    market_cols = ['Copper', 'Oil', 'DXY', 'SP500', 'VIX']
    for col in market_cols:
        if col in df_clean.columns:
            feature_cols.append(col)

    X = df_clean[feature_cols]
    y = df_clean['target']

    return X, y, feature_cols

def train_model_with_validation(X, y, horizon_days):
    """Train model with robust time series cross-validation"""
    print(f"\nTraining model for {horizon_days}-day horizon")
    print(f"Dataset size: {len(X)} samples")

    # Time Series Split for validation
    tscv = TimeSeriesSplit(n_splits=5)

    best_score = float('inf')
    best_params = None

    # Hyperparameters optimized for stability
    param_grid = [
        {
            'num_leaves': 15,
            'max_depth': 4,
            'learning_rate': 0.01,
            'n_estimators': 500,
            'min_child_samples': 30,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'reg_alpha': 1.0,  # L1 regularization
            'reg_lambda': 1.0,  # L2 regularization
        },
        {
            'num_leaves': 20,
            'max_depth': 5,
            'learning_rate': 0.02,
            'n_estimators': 300,
            'min_child_samples': 25,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.5,
            'reg_lambda': 0.5,
        }
    ]

    for params in param_grid:
        cv_scores = []

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)

            # Train model
            model = lgb.LGBMRegressor(**params, random_state=42, verbose=-1)
            model.fit(X_train_scaled, y_train)

            # Predict and evaluate
            y_pred = model.predict(X_val_scaled)

            # Calculate MAPE
            mape = np.mean(np.abs((y_val - y_pred) / y_val)) * 100
            cv_scores.append(mape)

        avg_mape = np.mean(cv_scores)
        print(f"Params {params['num_leaves']} leaves, depth {params['max_depth']}: MAPE = {avg_mape:.2f}%")

        if avg_mape < best_score:
            best_score = avg_mape
            best_params = params

    print(f"Best MAPE: {best_score:.2f}%")

    # Train final model on all data with best params
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    final_model = lgb.LGBMRegressor(**best_params, random_state=42, verbose=-1)
    final_model.fit(X_scaled, y)

    # Final evaluation on holdout set (last 20%)
    holdout_size = int(len(X) * 0.2)
    X_train_final = X_scaled[:-holdout_size]
    X_test_final = X_scaled[-holdout_size:]
    y_train_final = y.iloc[:-holdout_size]
    y_test_final = y.iloc[-holdout_size:]

    final_model_test = lgb.LGBMRegressor(**best_params, random_state=42, verbose=-1)
    final_model_test.fit(X_train_final, y_train_final)

    y_pred_test = final_model_test.predict(X_test_final)
    test_mape = np.mean(np.abs((y_test_final - y_pred_test) / y_test_final)) * 100

    print(f"Holdout Test MAPE: {test_mape:.2f}%")
    print(f"Accuracy: {100 - test_mape:.2f}%")

    return final_model, scaler, best_params, test_mape

def main():
    """Main training pipeline"""
    print("=" * 60)
    print("ML MODEL TRAINING - OPTIMIZED VERSION 3.0")
    print("=" * 60)

    # Load data
    print(f"\nLoading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    df = df.sort_index()

    # Merge FRED interest rate data (NEW 2025-11-22)
    FRED_PATH = BASE_DIR / "data" / "raw" / "fred_interest_rates.csv"
    if FRED_PATH.exists():
        fred_df = pd.read_csv(FRED_PATH, index_col=0, parse_dates=True)
        df = df.join(fred_df[["rate_differential"]], how="left")
        df["rate_differential"] = df["rate_differential"].ffill().bfill()
        print(f"Merged FRED: rate_differential [{df['rate_differential'].min():.2f}, {df['rate_differential'].max():.2f}]")

    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")

    # Clean data - remove extreme outliers
    df_clean = clean_data_remove_outliers(df, max_daily_change=0.03)

    # Train models for each horizon
    results = {}

    for horizon_name, horizon_days in HORIZONS.items():
        print(f"\n{'='*60}")
        print(f"TRAINING {horizon_name} MODEL")
        print(f"{'='*60}")

        # Prepare data
        X, y, feature_cols = prepare_data_for_horizon(df_clean, horizon_days)

        # Train model
        model, scaler, best_params, mape = train_model_with_validation(X, y, horizon_days)

        # Save model
        model_dir = MODELS_DIR / horizon_name
        model_dir.mkdir(parents=True, exist_ok=True)

        model_dict = {
            'model': model,
            'scaler': scaler,
            'features': feature_cols,
            'best_params': best_params,
            'mape': mape,
            'horizon_days': horizon_days
        }

        model_path = model_dir / "lightgbm_primary.joblib"
        joblib.dump(model_dict, model_path)
        print(f"\n✓ Model saved to {model_path}")

        results[horizon_name] = {
            'mape': mape,
            'accuracy': 100 - mape,
            'num_features': len(feature_cols)
        }

    # Print summary
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    for horizon, metrics in results.items():
        print(f"{horizon:5s} | MAPE: {metrics['mape']:5.2f}% | Accuracy: {metrics['accuracy']:5.2f}% | Features: {metrics['num_features']}")
    print("=" * 60)
    print("\n✅ Training completed successfully!")

if __name__ == "__main__":
    main()
