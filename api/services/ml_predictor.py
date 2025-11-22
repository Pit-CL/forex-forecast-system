"""
ML Predictor for forex forecasting using trained models
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class MLForecaster:
    """Forecaster using trained ML models"""

    def __init__(self, models_dir: Path = Path("/app/models/trained")):
        self.models_dir = models_dir
        self.models = {}

    def load_model(self, horizon: str) -> Dict:
        """Load trained model for specific horizon"""
        if horizon in self.models:
            return self.models[horizon]

        model_path = self.models_dir / horizon / "lightgbm_primary.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_dict = joblib.load(model_path)
        self.models[horizon] = model_dict
        return model_dict

    def create_features(self, data: pd.DataFrame, target_col='USDCLP') -> pd.DataFrame:
        """Create features matching training data"""
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
            df_feat['DXY_return_14'] = df_feat['DXY'].pct_change(periods=14)

        return df_feat

    def forecast_multistep(self, data: pd.DataFrame, horizon_days: int, model_dict: Dict) -> Tuple[List[float], List[float], List[float]]:
        """Generate multi-step forecast with confidence intervals and realistic constraints"""
        model = model_dict['model']
        scaler = model_dict['scaler']
        required_features = model_dict['features']

        predictions = []
        lower_bounds = []
        upper_bounds = []

        # Get current price for constraint calculations
        current_price = float(data['USDCLP'].dropna().iloc[-1])

        # Create copy for iterative prediction
        df_forecast = data.copy()

        # CONSTRAINTS: Maximum realistic daily change (2% per day)
        MAX_DAILY_CHANGE_PCT = 0.02  # 2% maximum daily change

        # Maximum cumulative change based on horizon
        max_horizon_changes = {
            7: 0.05,   # 5% max for 7 days
            15: 0.08,  # 8% max for 15 days
            30: 0.12,  # 12% max for 30 days
            90: 0.20   # 20% max for 90 days
        }
        max_total_change = max_horizon_changes.get(horizon_days, 0.15)

        for step in range(horizon_days):
            # Create features for current state
            df_with_features = self.create_features(df_forecast)

            # Get last row (most recent data)
            latest = df_with_features.iloc[-1]

            # Prepare features for prediction
            X = latest[required_features].values.reshape(1, -1)

            # Scale features
            X_scaled = scaler.transform(X)

            # Make prediction
            raw_pred = model.predict(X_scaled)[0]

            # Get previous price (for daily constraint)
            prev_price = float(df_forecast['USDCLP'].dropna().iloc[-1])

            # CONSTRAINT 1: Limit daily change to ±2%
            max_daily_price = prev_price * (1 + MAX_DAILY_CHANGE_PCT)
            min_daily_price = prev_price * (1 - MAX_DAILY_CHANGE_PCT)
            pred = np.clip(raw_pred, min_daily_price, max_daily_price)

            # CONSTRAINT 2: Limit total change from current price
            max_total_price = current_price * (1 + max_total_change)
            min_total_price = current_price * (1 - max_total_change)
            pred = np.clip(pred, min_total_price, max_total_price)

            predictions.append(pred)

            # Calculate confidence interval (gets wider over time)
            base_std = 5.0  # Base standard deviation
            time_factor = 1.0 + (step * 0.1)  # Increases with forecast horizon
            std = base_std * time_factor

            lower_bounds.append(pred - 1.96 * std)
            upper_bounds.append(pred + 1.96 * std)

            # Add prediction to dataframe for next iteration
            next_date = df_forecast.index[-1] + timedelta(days=1)
            new_row = df_forecast.iloc[-1].copy()
            new_row['USDCLP'] = pred

            # Append new row
            new_row_df = pd.DataFrame([new_row], index=[next_date])
            df_forecast = pd.concat([df_forecast, new_row_df])

        return predictions, lower_bounds, upper_bounds

    def generate_forecast(self, csv_path: Path, horizon: str) -> Dict:
        """Generate forecast for given horizon"""
        # Map horizon to days
        horizon_map = {'7D': 7, '15D': 15, '30D': 30, '90D': 90}
        horizon_days = horizon_map.get(horizon)

        if not horizon_days:
            raise ValueError(f"Invalid horizon: {horizon}")

        # Load model
        model_dict = self.load_model(horizon)

        # Load data
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df = df.sort_index()

        # Use last 200 days for context
        df_recent = df.tail(200)

        # Generate forecast
        predictions, lower, upper = self.forecast_multistep(df_recent, horizon_days, model_dict)

        # Prepare response - get most recent valid price
        current_price = float(df['USDCLP'].dropna().iloc[-1])
        forecast_price = predictions[-1]

        return {
            'current_price': current_price,
            'forecast_price': forecast_price,
            'predictions': predictions,
            'lower_bounds': lower,
            'upper_bounds': upper,
            'horizon': horizon,
            'horizon_days': horizon_days
        }
