"""
Market indicators and performance metrics router
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List
from pydantic import BaseModel
import random
import pandas as pd
import os
from pathlib import Path
import httpx

router = APIRouter(prefix="/api", tags=["market"])

class MarketIndicator(BaseModel):
    """Market indicator data model"""
    name: str
    value: float
    change_24h: float
    timestamp: datetime

class PerformanceMetrics(BaseModel):
    """Performance metrics for forecast models"""
    model: str
    mae: float
    rmse: float
    mape: float
    directional_accuracy: float

@router.get("/market-data")
async def get_market_data():
    """Get real market data from CSV - returns flat structure for frontend"""
    try:
        # Determine data path based on environment
        if os.getenv("ENVIRONMENT") == "development":
            data_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-systemV2/data/raw/yahoo_finance_data.csv")
        else:
            data_path = Path("/app/data/raw/yahoo_finance_data.csv")
        
        # Read CSV
        df = pd.read_csv(data_path)
        
        # Get latest row
        # Get last row for market indicators
        latest = df.iloc[-1]
        
        # For USDCLP, get last non-null value
        last_usdclp = df["USDCLP"].dropna().iloc[-1] if not df["USDCLP"].dropna().empty else None
        
        # Return flat structure matching frontend expectations
        return {
            "Date": str(latest["Date"]) if "Date" in latest and not pd.isna(latest["Date"]) else None,
            "USDCLP": float(last_usdclp) if last_usdclp is not None else None,
            "Copper": float(latest["Copper"]) if not pd.isna(latest["Copper"]) else None,
            "Oil": float(latest["Oil"]) if not pd.isna(latest["Oil"]) else None,
            "DXY": float(latest["DXY"]) if not pd.isna(latest["DXY"]) else None,
            "SP500": float(latest["SP500"]) if not pd.isna(latest["SP500"]) else None,
            "VIX": float(latest["VIX"]) if not pd.isna(latest["VIX"]) else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading market data: {str(e)}")

@router.get("/indicators")
async def get_indicators() -> List[MarketIndicator]:
    """Get current market indicators (mock data for now)"""
    base_time = datetime.now()
    
    indicators = [
        MarketIndicator(
            name="RSI",
            value=round(random.uniform(30, 70), 2),
            change_24h=round(random.uniform(-5, 5), 2),
            timestamp=base_time
        ),
        MarketIndicator(
            name="MACD",
            value=round(random.uniform(-2, 2), 2),
            change_24h=round(random.uniform(-0.5, 0.5), 2),
            timestamp=base_time
        ),
        MarketIndicator(
            name="Bollinger Bands",
            value=round(random.uniform(900, 950), 2),
            change_24h=round(random.uniform(-10, 10), 2),
            timestamp=base_time
        )
    ]
    
    return indicators

@router.get("/performance")
async def get_performance() -> List[PerformanceMetrics]:
    """Get model performance metrics by horizon"""
    # Try to get real metrics from forecasts endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/forecasts", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                forecasts = data.get("forecasts", {})
                
                metrics = []
                horizon_map = {
                    "7d": "7D",
                    "15d": "15D",
                    "30d": "30D",
                    "90d": "90D"
                }
                
                for horizon_key, horizon_label in horizon_map.items():
                    if horizon_key in forecasts:
                        forecast_data = forecasts[horizon_key]
                        metadata = forecast_data.get("metadata", {})
                        
                        # Get MAPE from metadata
                        mape = metadata.get("mape", 5.0)
                        accuracy = metadata.get("accuracy_score", 0.95)
                        
                        # Calculate other metrics (mock for now)
                        mae = mape * 2.5  # Rough estimate
                        rmse = mape * 3.0  # Rough estimate
                        
                        metrics.append(PerformanceMetrics(
                            model=f"ARIMA {horizon_label}",
                            mae=round(mae, 2),
                            rmse=round(rmse, 2),
                            mape=round(mape, 2),
                            directional_accuracy=round(accuracy, 4)
                        ))
                
                if metrics:
                    return metrics
    except Exception as e:
        print(f"Error fetching real metrics: {e}")
    
    # Fallback to mock data by horizon
    return [
        PerformanceMetrics(
            model="ARIMA 7D",
            mae=12.90,
            rmse=15.48,
            mape=5.16,
            directional_accuracy=0.9484
        ),
        PerformanceMetrics(
            model="ARIMA 15D",
            mae=15.83,
            rmse=19.00,
            mape=6.33,
            directional_accuracy=0.9316
        ),
        PerformanceMetrics(
            model="ARIMA 30D",
            mae=19.25,
            rmse=23.10,
            mape=7.70,
            directional_accuracy=0.9026
        ),
        PerformanceMetrics(
            model="ARIMA 90D",
            mae=28.50,
            rmse=34.20,
            mape=11.40,
            directional_accuracy=0.8530
        )
    ]
