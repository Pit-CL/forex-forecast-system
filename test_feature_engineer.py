"""
Test script for feature_engineer.py

Validates that feature engineering works correctly with synthetic data.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from forex_core.features import engineer_features, validate_features


def create_test_data(n_days: int = 200) -> pd.DataFrame:
    """Create synthetic test data."""
    np.random.seed(42)

    dates = pd.date_range(start='2023-01-01', periods=n_days, freq='D')

    # Generate realistic-looking data
    usdclp_base = 920
    usdclp_trend = np.linspace(0, 30, n_days)  # Upward trend
    usdclp_noise = np.random.normal(0, 5, n_days)
    usdclp = usdclp_base + usdclp_trend + usdclp_noise

    copper_base = 4.0
    copper_trend = np.linspace(0, 0.5, n_days)
    copper_noise = np.random.normal(0, 0.15, n_days)
    copper = copper_base + copper_trend + copper_noise

    df = pd.DataFrame({
        'date': dates,
        'usdclp': usdclp,
        'copper_price': copper,
        'copper_volume': np.random.uniform(5000, 15000, n_days),
        'dxy': np.random.uniform(102, 106, n_days),
        'vix': np.random.uniform(12, 25, n_days),
        'tpm': [5.75] * n_days,  # Chilean rate
        'fed_funds': [5.25] * n_days,  # US rate
        'imacec': np.random.uniform(3500, 3700, n_days),
        'ipc': np.linspace(100, 105, n_days),  # Inflation
    })

    return df


def main():
    """Run feature engineering test."""
    print("=" * 60)
    print("Feature Engineering Test")
    print("=" * 60)

    # Create test data
    print("\n1. Creating synthetic test data...")
    df = create_test_data(n_days=200)
    print(f"   Created {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")

    # Engineer features
    print("\n2. Engineering features...")
    try:
        features_df = engineer_features(df, horizon=7)
        print(f"   SUCCESS: Generated {len(features_df.columns)} total columns")
        print(f"   Rows after processing: {len(features_df)}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Show feature categories
    print("\n3. Feature categories:")

    # Lagged features
    lag_features = [col for col in features_df.columns if 'lag' in col]
    print(f"   - Lagged features: {len(lag_features)}")
    print(f"     Examples: {lag_features[:5]}")

    # Technical indicators
    tech_features = [col for col in features_df.columns
                     if any(x in col for x in ['sma', 'ema', 'rsi', 'bb', 'atr', 'macd'])]
    print(f"   - Technical indicators: {len(tech_features)}")
    print(f"     Examples: {tech_features[:5]}")

    # Copper features
    copper_features = [col for col in features_df.columns if 'copper' in col]
    print(f"   - Copper features: {len(copper_features)}")
    print(f"     Examples: {copper_features[:5]}")

    # Macro features
    macro_features = [col for col in features_df.columns
                      if any(x in col for x in ['dxy', 'vix', 'tpm', 'fed', 'rate_diff'])]
    print(f"   - Macro features: {len(macro_features)}")
    print(f"     Examples: {macro_features[:5]}")

    # Derived features
    derived_features = [col for col in features_df.columns
                        if any(x in col for x in ['return', 'volatility', 'trend', 'day_', 'month', 'dist'])]
    print(f"   - Derived features: {len(derived_features)}")
    print(f"     Examples: {derived_features[:5]}")

    # Validate features
    print("\n4. Validating features...")
    if validate_features(features_df):
        print("   VALIDATION PASSED")
    else:
        print("   VALIDATION FAILED")
        return

    # Data quality metrics
    print("\n5. Data quality metrics:")
    nan_pct = features_df.isna().sum().sum() / (len(features_df) * len(features_df.columns)) * 100
    print(f"   - NaN percentage: {nan_pct:.3f}%")
    print(f"   - Infinite values: {np.isinf(features_df.select_dtypes(include=[np.number])).sum().sum()}")
    print(f"   - Duplicate dates: {features_df.index.duplicated().sum()}")

    # Show sample of engineered features
    print("\n6. Sample of engineered features (last 5 rows):")
    sample_cols = ['usdclp', 'usdclp_lag1', 'usdclp_sma5', 'usdclp_rsi14',
                   'usdclp_return_1d', 'copper_price', 'copper_rsi14', 'rate_differential']
    available_cols = [col for col in sample_cols if col in features_df.columns]
    print(features_df[available_cols].tail().to_string())

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Total features: {len(features_df.columns)}")
    print(f"  - Numeric features: {len(features_df.select_dtypes(include=[np.number]).columns)}")
    print(f"  - Valid rows: {len(features_df)}")
    print(f"  - Data quality: {100 - nan_pct:.2f}% complete")


if __name__ == '__main__':
    main()
