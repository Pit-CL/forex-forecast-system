"""
Forecasts router for API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import ForecastResponse, MultiHorizonForecast, ErrorResponse
from services.forecast_service import ForecastService

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])
forecast_service = ForecastService()


@router.get("", response_model=MultiHorizonForecast)
async def get_all_forecasts():
    """
    Get forecasts for all time horizons (7d, 15d, 30d, 90d)
    """
    try:
        forecasts = await forecast_service.get_all_forecasts()
        return forecasts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{horizon}", response_model=ForecastResponse)
async def get_forecast_by_horizon(horizon: str):
    """
    Get forecast for specific time horizon

    Parameters:
    - horizon: Time horizon (7d, 15d, 30d, 90d)
    """
    if horizon not in ["7d", "15d", "30d", "90d"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid horizon: {horizon}. Must be one of: 7d, 15d, 30d, 90d"
        )

    try:
        forecast = await forecast_service.get_forecast(horizon)
        if not forecast:
            raise HTTPException(status_code=404, detail=f"Forecast not found for horizon: {horizon}")
        return forecast
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy/metrics")
async def get_accuracy_metrics():
    """
    Get historical accuracy metrics for all forecast horizons
    """
    try:
        metrics = await forecast_service.get_forecast_accuracy_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))