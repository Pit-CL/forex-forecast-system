"""
Data service for handling historical data and technical indicators
"""
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from models.schemas import (
    HistoricalPoint,
    HistoricalResponse,
    TechnicalIndicator,
    IndicatorsResponse,
    MarketDriver,
    DriversResponse
)
from utils.config import settings


class DataService:
    """Service for managing historical data and indicators"""

    def __init__(self):
        self.warehouse_path = settings.warehouse_path
        self.development_mode = settings.development_mode
        self.data_path = settings.data_path

    def _load_csv_data(self) -> pd.DataFrame:
        """Load real data from CSV file"""
        try:
            # First try mindicador_data.csv for more recent data
            mindicador_path = self.data_path / "raw" / "mindicador_data.csv"
            if mindicador_path.exists():
                df_mindicador = pd.read_csv(mindicador_path, parse_dates=['date'])
                df_mindicador = df_mindicador.rename(columns={'dolar': 'USDCLP'})
                df_mindicador = df_mindicador.set_index('date')
                df_mindicador = df_mindicador[['USDCLP']].dropna()
                # Remove timezone info to match yahoo data format
                df_mindicador.index = df_mindicador.index.tz_localize(None)

                # Also load yahoo_finance_data for older historical data
                yahoo_path = self.data_path / "raw" / "yahoo_finance_data.csv"
                if yahoo_path.exists():
                    df_yahoo = pd.read_csv(yahoo_path, index_col=0, parse_dates=True)
                    df_yahoo = df_yahoo[['USDCLP']]

                    # Combine both datasets (mindicador has priority for overlapping dates)
                    df = pd.concat([df_yahoo, df_mindicador])
                    df = df[~df.index.duplicated(keep='last')]  # Keep mindicador data for duplicates
                    df = df.sort_index()
                    return df
                else:
                    return df_mindicador.sort_index()

            # Fallback to yahoo_finance_data.csv
            csv_path = self.data_path / "raw" / "yahoo_finance_data.csv"

            if not csv_path.exists():
                print(f"CSV file not found at {csv_path}")
                return pd.DataFrame()

            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            df = df.sort_index()
            return df
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            return pd.DataFrame()

    def _generate_mock_historical_data(self, days: int = 30) -> List[HistoricalPoint]:
        """Generate mock historical OHLC data"""
        data = []
        current_date = datetime.now().date()
        base_price = 950.0

        for i in range(days, 0, -1):
            # Generate realistic OHLC data
            daily_change = random.gauss(0, 0.01)  # 1% daily volatility
            open_price = base_price * (1 + random.gauss(0, 0.002))
            close_price = open_price * (1 + daily_change)

            # High and low around the open-close range
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.003)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.003)))

            data.append(HistoricalPoint(
                date=current_date - timedelta(days=i),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=random.uniform(100000, 500000)
            ))

            base_price = close_price

        return data

    async def get_historical_data(self, period_days: int = 30) -> HistoricalResponse:
        """Get historical price data"""
        # Try to load real data from CSV first
        df = self._load_csv_data()
        
        historical_data = []
        
        if not df.empty and 'USDCLP' in df.columns:
            try:
                # Get last N days
                df_recent = df.tail(period_days)

                # Convert to HistoricalPoint format
                for date_idx, row in df_recent.iterrows():
                    if pd.notna(row['USDCLP']):
                        # Calculate OHLC from daily close (deterministic approximation)
                        close = float(row['USDCLP'])
                        
                        # Validate close price
                        if not np.isfinite(close) or close <= 0:
                            continue

                        # Use deterministic seed based on date to ensure consistency
                        seed = int(date_idx.strftime("%Y%m%d"))
                        rng = np.random.default_rng(seed)

                        # Generate deterministic OHLC variations
                        open_var = rng.uniform(0, 0.003)
                        high_var = rng.uniform(0, 0.005)
                        low_var = rng.uniform(0, 0.005)

                        open_price = close * (1 - open_var)
                        high_price = close * (1 + high_var)
                        low_price = close * (1 - low_var)
                        volume = int(250000 + (seed % 100000))

                        # Validate all values
                        if all(np.isfinite([open_price, high_price, low_price, close])):
                            historical_data.append(HistoricalPoint(
                                date=date_idx.date(),
                                open=round(float(open_price), 2),
                                high=round(float(high_price), 2),
                                low=round(float(low_price), 2),
                                close=round(float(close), 2),
                                volume=volume,
                            ))
            except Exception as e:
                print(f"Error processing historical data: {e}")

        # Fallback to mock data if no real data available
        if len(historical_data) == 0:
            print("No real data available, using mock data")
            historical_data = self._generate_mock_historical_data(period_days)

        # Calculate statistics
        closes = [point.close for point in historical_data]
        
        if len(closes) > 1:
            log_returns = np.diff(np.log(closes))
            volatility = float(np.std(log_returns) * np.sqrt(252) * 100) if len(log_returns) > 0 else 0.0
        else:
            volatility = 0.0
        
        statistics = {
            "mean": round(float(np.mean(closes)), 2),
            "std": round(float(np.std(closes)), 2),
            "min": round(float(min(closes)), 2),
            "max": round(float(max(closes)), 2),
            "volatility": round(volatility, 2),
            "trend": "upward" if closes[-1] > closes[0] else "downward"
        }

        return HistoricalResponse(
            symbol="USD/CLP",
            period=f"{period_days}d",
            data=historical_data,
            statistics=statistics
        )

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period:
            return 50.0

        deltas = np.diff(prices[-period-1:])
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            return 100.0

        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _calculate_macd(self, prices: List[float]) -> Dict:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}

        # Simple exponential moving averages
        ema_12 = pd.Series(prices).ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = pd.Series(prices).ewm(span=26, adjust=False).mean().iloc[-1]

        macd = ema_12 - ema_26
        signal = pd.Series([macd]).ewm(span=9, adjust=False).mean().iloc[-1]
        histogram = macd - signal

        return {
            "macd": round(macd, 2),
            "signal": round(signal, 2),
            "histogram": round(histogram, 2)
        }

    async def get_technical_indicators(self) -> IndicatorsResponse:
        """Calculate and return technical indicators"""
        # Get recent historical data
        hist_data = await self.get_historical_data(50)
        prices = [point.close for point in hist_data.data]
        current_price = prices[-1]

        # Calculate indicators
        rsi = self._calculate_rsi(prices)
        macd_data = self._calculate_macd(prices)

        # Simple moving averages
        sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else current_price
        sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else current_price

        # Bollinger Bands
        bb_period = 20
        if len(prices) >= bb_period:
            bb_mean = np.mean(prices[-bb_period:])
            bb_std = np.std(prices[-bb_period:])
            bb_upper = bb_mean + (2 * bb_std)
            bb_lower = bb_mean - (2 * bb_std)
        else:
            bb_upper = bb_lower = current_price

        indicators = []

        # RSI indicator
        rsi_signal = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        indicators.append(TechnicalIndicator(
            name="RSI",
            value=rsi,
            signal=rsi_signal,
            strength=abs(rsi - 50) / 50
        ))

        # MACD indicator
        macd_signal = "buy" if macd_data["histogram"] > 0 else "sell"
        indicators.append(TechnicalIndicator(
            name="MACD",
            value=macd_data["macd"],
            signal=macd_signal,
            strength=min(abs(macd_data["histogram"]) / 10, 1.0)
        ))

        # Moving Average indicator
        ma_signal = "buy" if current_price > sma_20 else "sell"
        indicators.append(TechnicalIndicator(
            name="SMA20",
            value=round(sma_20, 2),
            signal=ma_signal,
            strength=abs(current_price - sma_20) / sma_20
        ))

        # Bollinger Bands indicator
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        bb_signal = "oversold" if bb_position < 0.2 else "overbought" if bb_position > 0.8 else "neutral"
        indicators.append(TechnicalIndicator(
            name="Bollinger Bands",
            value=round(bb_position * 100, 2),
            signal=bb_signal,
            strength=abs(bb_position - 0.5) * 2
        ))

        # Calculate overall signal
        buy_signals = sum(1 for ind in indicators if ind.signal in ["buy", "oversold"])
        sell_signals = sum(1 for ind in indicators if ind.signal in ["sell", "overbought"])

        if buy_signals > sell_signals:
            overall_signal = "buy"
        elif sell_signals > buy_signals:
            overall_signal = "sell"
        else:
            overall_signal = "neutral"

        overall_strength = np.mean([ind.strength for ind in indicators])

        return IndicatorsResponse(
            timestamp=datetime.now(),
            symbol="USD/CLP",
            current_price=current_price,
            indicators=indicators,
            overall_signal=overall_signal,
            overall_strength=round(overall_strength, 2)
        )

    async def get_market_drivers(self) -> DriversResponse:
        """Get market drivers data"""
        # Mock market drivers data
        drivers = [
            MarketDriver(
                name="Copper",
                symbol="HG",
                current_value=round(4.20 + random.uniform(-0.1, 0.1), 3),
                change_24h=round(random.uniform(-0.05, 0.05), 3),
                change_pct_24h=round(random.uniform(-2, 2), 2),
                correlation=0.65,
                impact="negative" if random.random() > 0.5 else "positive"
            ),
            MarketDriver(
                name="US Dollar Index",
                symbol="DXY",
                current_value=round(104.5 + random.uniform(-1, 1), 2),
                change_24h=round(random.uniform(-0.5, 0.5), 2),
                change_pct_24h=round(random.uniform(-0.5, 0.5), 2),
                correlation=0.82,
                impact="positive" if random.random() > 0.5 else "negative"
            ),
            MarketDriver(
                name="Chilean 10Y Bond",
                symbol="CL10Y",
                current_value=round(5.2 + random.uniform(-0.2, 0.2), 2),
                change_24h=round(random.uniform(-0.1, 0.1), 2),
                change_pct_24h=round(random.uniform(-2, 2), 2),
                correlation=-0.45,
                impact="neutral"
            ),
            MarketDriver(
                name="US 10Y Treasury",
                symbol="US10Y",
                current_value=round(4.3 + random.uniform(-0.1, 0.1), 2),
                change_24h=round(random.uniform(-0.05, 0.05), 2),
                change_pct_24h=round(random.uniform(-1, 1), 2),
                correlation=0.55,
                impact="positive" if random.random() > 0.5 else "negative"
            ),
            MarketDriver(
                name="Oil (WTI)",
                symbol="CL",
                current_value=round(75.0 + random.uniform(-2, 2), 2),
                change_24h=round(random.uniform(-1, 1), 2),
                change_pct_24h=round(random.uniform(-2, 2), 2),
                correlation=-0.35,
                impact="neutral"
            )
        ]

        return DriversResponse(
            timestamp=datetime.now(),
            drivers=drivers
        )
