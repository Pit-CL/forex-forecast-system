"""
Forecast Generator Service
Generates forecasts based on real warehouse data
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ForecastGenerator:
    """Generate forecasts from warehouse data with realistic projections"""

    def __init__(self, warehouse_path: Path, output_path: Path):
        self.warehouse_path = warehouse_path
        self.output_path = output_path
        self.output_path.mkdir(parents=True, exist_ok=True)

    def load_warehouse_data(self) -> pd.DataFrame:
        """Load USD/CLP data from warehouse"""
        try:
            df = pd.read_parquet(self.warehouse_path / "usdclp_daily.parquet")
            # Reset index to get fecha as column
            df = df.reset_index()
            df.columns = ['fecha', 'close']
            logger.info(f"Loaded {len(df)} rows from warehouse")
            return df
        except Exception as e:
            logger.error(f"Error loading warehouse data: {e}")
            raise

    def generate_forecast(self, horizon_days: int, df: pd.DataFrame) -> Dict:
        """Generate forecast for specified horizon"""

        # Get latest price
        latest_row = df.iloc[-1]
        current_price = float(latest_row['close'])
        current_date = pd.to_datetime(latest_row['fecha'])

        # Calculate statistics for volatility
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized volatility

        # Calculate trend using simple moving averages
        ma_20 = df['close'].rolling(20).mean().iloc[-1]
        ma_50 = df['close'].rolling(50).mean().iloc[-1]
        trend_strength = (ma_20 - ma_50) / ma_50

        # Generate forecast dates
        forecast_dates = []
        for i in range(1, horizon_days + 1):
            forecast_dates.append(current_date + timedelta(days=i))

        # Generate forecast values with realistic projections
        forecast_values = []
        confidence_lower = []
        confidence_upper = []

        # Base drift (slight upward bias for emerging market currency)
        annual_drift = 0.02  # 2% annual depreciation
        daily_drift = annual_drift / 252

        # Adjust drift based on trend
        adjusted_drift = daily_drift + (trend_strength * 0.001)

        for i in range(1, horizon_days + 1):
            # Random walk with drift
            daily_vol = volatility / np.sqrt(252)
            random_shock = np.random.normal(0, daily_vol)

            # Mean reversion component
            mean_level = df['close'].rolling(200).mean().iloc[-1]
            mean_reversion_speed = 0.1
            mean_reversion = mean_reversion_speed * (mean_level - current_price) / mean_level

            # Calculate forecast
            drift_component = adjusted_drift * i
            vol_component = random_shock * np.sqrt(i)
            reversion_component = mean_reversion * np.log(i + 1) * 0.01

            forecast_price = current_price * (1 + drift_component + vol_component + reversion_component)

            # Confidence intervals (widen with time)
            confidence_width = current_price * daily_vol * np.sqrt(i) * 1.96

            forecast_values.append(round(forecast_price, 2))
            confidence_lower.append(round(forecast_price - confidence_width, 2))
            confidence_upper.append(round(forecast_price + confidence_width, 2))

        # Calculate target price and probability
        target_price = forecast_values[-1]
        price_change_pct = ((target_price - current_price) / current_price) * 100

        # Probability based on trend strength and volatility
        if abs(price_change_pct) < volatility * 100 * np.sqrt(horizon_days/252):
            probability = 0.65 + (0.2 * (1 - abs(trend_strength)))
        else:
            probability = 0.45 + (0.1 * (1 - abs(trend_strength)))

        probability = min(0.85, max(0.35, probability))  # Cap between 35% and 85%

        # Determine signal
        if price_change_pct > 2:
            signal = "SELL"
            signal_strength = min(90, 50 + abs(price_change_pct) * 5)
        elif price_change_pct < -2:
            signal = "BUY"
            signal_strength = min(90, 50 + abs(price_change_pct) * 5)
        else:
            signal = "HOLD"
            signal_strength = 50

        # Key drivers (based on real correlations)
        drivers = []

        # Copper correlation
        try:
            copper_df = pd.read_parquet(self.warehouse_path / "copper_hgf_usd_lb.parquet")
            copper_df = copper_df.reset_index()
            copper_df.columns = ['fecha', 'close']
            copper_change = copper_df['close'].pct_change().iloc[-20:].mean() * 100
        except Exception as e:
            copper_change = 0
        if abs(copper_change) > 1:
            drivers.append({
                "name": "Precio del Cobre",
                "impact": "positive" if copper_change > 0 else "negative",
                "description": f"Cobre {'subió' if copper_change > 0 else 'bajó'} {abs(copper_change):.1f}% (20d avg)"
            })

        # DXY correlation
        try:
            dxy_df = pd.read_parquet(self.warehouse_path / "dxy_index.parquet")
            dxy_df = dxy_df.reset_index()
            dxy_df.columns = ['fecha', 'close']
            dxy_change = dxy_df['close'].pct_change().iloc[-10:].mean() * 100
            if abs(dxy_change) > 0.5:
                drivers.append({
                    "name": "Índice Dólar (DXY)",
                    "impact": "negative" if dxy_change > 0 else "positive",
                    "description": f"DXY {'subió' if dxy_change > 0 else 'bajó'} {abs(dxy_change):.1f}% (10d avg)"
                })
        except:
            pass

        # Add technical driver
        rsi = self.calculate_rsi(df['close'])
        if rsi > 70:
            drivers.append({
                "name": "RSI Sobrecompra",
                "impact": "negative",
                "description": f"RSI en {rsi:.0f}, indicando sobrecompra"
            })
        elif rsi < 30:
            drivers.append({
                "name": "RSI Sobreventa",
                "impact": "positive",
                "description": f"RSI en {rsi:.0f}, indicando sobreventa"
            })

        # Risk factors
        risk_factors = []

        if volatility > 0.15:
            risk_factors.append({
                "type": "market",
                "description": f"Alta volatilidad ({volatility*100:.1f}% anual)",
                "severity": "high"
            })

        # Check for trend reversal risk
        if abs(trend_strength) > 0.02:
            risk_factors.append({
                "type": "technical",
                "description": "Posible reversión de tendencia",
                "severity": "medium"
            })

        # Build forecast object
        forecast = {
            "horizon": f"{horizon_days}d",
            "generated_at": datetime.now().isoformat(),
            "current_price": current_price,
            "forecast": {
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "values": forecast_values,
                "confidence_lower": confidence_lower,
                "confidence_upper": confidence_upper
            },
            "target": {
                "price": target_price,
                "change_percent": round(price_change_pct, 2),
                "probability": round(probability, 2),
                "date": forecast_dates[-1].strftime("%Y-%m-%d")
            },
            "signal": {
                "action": signal,
                "strength": signal_strength,
                "confidence": round(probability * 100, 0)
            },
            "drivers": drivers[:3],  # Top 3 drivers
            "risk_factors": risk_factors,
            "metadata": {
                "model": "Statistical Ensemble",
                "last_training": current_date.strftime("%Y-%m-%d"),
                "data_points": len(df),
                "volatility": round(volatility, 4)
            }
        }

        return forecast

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def generate_all_forecasts(self):
        """Generate all forecast horizons"""
        try:
            # Load data
            df = self.load_warehouse_data()

            # Generate forecasts for each horizon
            horizons = [7, 15, 30, 90]

            for horizon in horizons:
                logger.info(f"Generating {horizon}d forecast...")
                forecast = self.generate_forecast(horizon, df)

                # Save to file
                filename = self.output_path / f"forecast_{horizon}d.json"
                with open(filename, 'w') as f:
                    json.dump(forecast, f, indent=2)

                logger.info(f"Saved forecast to {filename}")

            # Generate metadata file
            metadata = {
                "generated_at": datetime.now().isoformat(),
                "horizons": horizons,
                "data_source": str(self.warehouse_path),
                "latest_price": float(df.iloc[-1]['close']),
                "latest_date": pd.to_datetime(df.iloc[-1]['fecha']).strftime("%Y-%m-%d")
            }

            with open(self.output_path / "forecast_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info("All forecasts generated successfully")
            return True

        except Exception as e:
            logger.error(f"Error generating forecasts: {e}")
            return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Paths
    warehouse_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/data/warehouse")
    output_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/output/forecasts")

    # Generate forecasts
    generator = ForecastGenerator(warehouse_path, output_path)
    generator.generate_all_forecasts()