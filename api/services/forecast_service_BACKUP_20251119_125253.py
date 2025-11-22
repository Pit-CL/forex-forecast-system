"""
Forecast service for handling prediction data
"""
import json
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import joblib

from models.schemas import ForecastPoint, ForecastResponse, MultiHorizonForecast
from utils.config import settings


class ForecastService:
    """Service for managing forecast data"""

    def __init__(self):
        self.output_path = settings.output_path
        self.development_mode = settings.development_mode
        self._current_price_cache = None
        self._cache_timestamp = None
        self._models_cache = {}  # Cache para modelos ML

    def _get_real_current_price(self) -> float:
        """Get real current price from CSV data with caching"""
        # Cache for 5 minutes to avoid reading file on every request
        if self._current_price_cache and self._cache_timestamp:
            if (datetime.now() - self._cache_timestamp).seconds < 300:
                return self._current_price_cache

        try:
            # Use settings path in production, fallback to local path in development
            if settings.development_mode:
                csv_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-systemV2/data/raw/yahoo_finance_data.csv")
            else:
                csv_path = settings.data_path / "raw" / "yahoo_finance_data.csv"

            if csv_path.exists():
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                df = df.sort_index()
                # Get most recent USDCLP value
                latest = df['USDCLP'].dropna().iloc[-1]
                self._current_price_cache = float(latest)
                self._cache_timestamp = datetime.now()
                return self._current_price_cache
        except Exception as e:
            print(f"Error loading real current price: {e}")

        # Fallback to reasonable default
        return 930.0

    def _load_ml_model(self, horizon: str) -> Optional[Dict]:
        """Load trained ML model for specific horizon"""
        if horizon in self._models_cache:
            return self._models_cache[horizon]

        try:
            # Map horizon to uppercase format (7D, 15D, etc)
            horizon_upper = horizon.upper()

            # Path to model based on environment
            if self.development_mode:
                model_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-systemV2/models/trained") / horizon_upper / "lightgbm_primary.joblib"
            else:
                model_path = Path("/app/models/trained") / horizon_upper / "lightgbm_primary.joblib"

            if not model_path.exists():
                print(f"Model not found: {model_path}")
                return None

            model_dict = joblib.load(model_path)
            self._models_cache[horizon] = model_dict
            return model_dict

        except Exception as e:
            print(f"Error loading ML model for {horizon}: {e}")
            return None

    def _generate_mock_forecast(self, horizon_days: int, base_price: float = 950.0) -> List[ForecastPoint]:
        """Generate deterministic forecast data for development"""
        forecast_data = []
        current_date = datetime.now().date()

        # Use deterministic seed based on current date and horizon to ensure consistency
        seed = int(current_date.strftime("%Y%m%d")) + horizon_days
        rng = np.random.default_rng(seed)

        # Generate realistic trend with deterministic randomness
        trend = rng.choice([1, -1]) * rng.uniform(0.001, 0.003)

        for i in range(horizon_days):
            # Add daily volatility
            daily_change = trend + rng.normal(0, 0.005)
            base_price *= (1 + daily_change)

            # Calculate confidence bounds (wider for longer horizons)
            confidence_width = 10 + (i * 0.5)

            forecast_data.append(ForecastPoint(
                date=current_date + timedelta(days=i+1),
                value=round(base_price, 2),
                lower_bound=round(base_price - confidence_width, 2),
                upper_bound=round(base_price + confidence_width, 2)
            ))

        return forecast_data

    async def get_forecast(self, horizon: str) -> Optional[ForecastResponse]:
        """Get forecast for specific horizon"""
        horizon_map = {
            "7d": 7,
            "15d": 15,
            "30d": 30,
            "90d": 90
        }

        if horizon not in horizon_map:
            return None

        horizon_days = horizon_map[horizon]

        # Try to load real forecast data
        forecast_file = self.output_path / "forecasts" / f"forecast_{horizon}.json"
        if forecast_file.exists():
            try:
                with open(forecast_file, 'r') as f:
                    data = json.load(f)

                    # Parse real forecast data
                    forecast_points = []
                    for i, date_str in enumerate(data['forecast']['dates']):
                        forecast_points.append(ForecastPoint(
                            date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                            value=data['forecast']['values'][i],
                            lower_bound=data['forecast']['confidence_lower'][i],
                            upper_bound=data['forecast']['confidence_upper'][i]
                        ))

                    return ForecastResponse(
                        horizon=horizon,
                        horizon_days=horizon_days,
                        current_price=data['current_price'],
                        forecast_price=data['target']['price'],
                        price_change=data['target']['price'] - data['current_price'],
                        price_change_pct=data['target']['change_percent'],
                        confidence_level=data['target']['probability'],
                        forecast_date=datetime.fromisoformat(data['generated_at']),
                        data=forecast_points,
                        metadata=data.get('metadata', {})
                    )
            except Exception as e:
                print(f"Error loading forecast: {e}")

        # Try to load ML model and get real metrics
        model_dict = self._load_ml_model(horizon)

        if model_dict:
            # Use real MAPE and accuracy from trained model
            mape = model_dict.get('mape', 5.0)
            accuracy_score = (100 - mape) / 100  # Convert MAPE to accuracy (0-1)
            model_name = "LightGBM"
        else:
            # Fallback to mock values if model not found
            mape_scores = {7: 5.16, 15: 7.07, 30: 8.52, 90: 10.07}
            mape = mape_scores.get(horizon_days, 8.0)
            accuracy_score = (100 - mape) / 100
            model_name = "ARIMA" if horizon_days <= 30 else "Prophet"

        # Generate mock data for development using REAL current price
        current_price = self._get_real_current_price()
        forecast_data = self._generate_mock_forecast(horizon_days, current_price)

        # Calculate summary statistics
        last_forecast = forecast_data[-1].value
        price_change = last_forecast - current_price
        price_change_pct = (price_change / current_price) * 100

        return ForecastResponse(
            horizon=horizon,
            horizon_days=horizon_days,
            current_price=round(current_price, 2),
            forecast_price=round(last_forecast, 2),
            price_change=round(price_change, 2),
            price_change_pct=round(price_change_pct, 2),
            confidence_level=0.95,
            forecast_date=datetime.now(),
            data=forecast_data,
            metadata={
                "model": model_name,
                "last_updated": datetime.now().isoformat(),
                "accuracy_score": accuracy_score,
                "mape": mape
            }
        )

    async def get_all_forecasts(self) -> MultiHorizonForecast:
        """Get forecasts for all horizons"""
        horizons = ["7d", "15d", "30d", "90d"]
        forecasts = {}
        # Use REAL current price from CSV data
        current_price = self._get_real_current_price()

        for horizon in horizons:
            forecast = await self.get_forecast(horizon)
            if forecast:
                # Ensure consistent current price across all horizons
                forecast.current_price = round(current_price, 2)
                forecasts[horizon] = forecast

        return MultiHorizonForecast(
            timestamp=datetime.now(),
            current_price=round(current_price, 2),
            forecasts=forecasts
        )

    async def get_forecast_accuracy_metrics(self) -> Dict:
        """Get historical accuracy metrics for forecasts"""
        # Deterministic accuracy metrics for development
        return {
            "7d": {
                "mae": 8.5,
                "rmse": 12.3,
                "mape": 0.92,
                "hit_rate": 0.87
            },
            "15d": {
                "mae": 14.2,
                "rmse": 19.7,
                "mape": 1.54,
                "hit_rate": 0.82
            },
            "30d": {
                "mae": 22.8,
                "rmse": 28.5,
                "mape": 2.45,
                "hit_rate": 0.76
            },
            "90d": {
                "mae": 35.6,
                "rmse": 45.2,
                "mape": 3.82,
                "hit_rate": 0.68
            }
        }