"""
Technical indicators router for API endpoints
"""
from fastapi import APIRouter, HTTPException

from models import IndicatorsResponse
from services.data_service import DataService

router = APIRouter(prefix="/api/indicators", tags=["indicators"])
data_service = DataService()


@router.get("", response_model=IndicatorsResponse)
async def get_technical_indicators():
    """
    Get current technical indicators for USD/CLP

    Returns indicators including:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Moving Averages (SMA20, SMA50)
    - Bollinger Bands
    - Overall signal and strength
    """
    try:
        indicators = await data_service.get_technical_indicators()
        return indicators
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_indicators_summary():
    """
    Get summarized technical analysis

    Returns a simplified view with buy/sell/neutral signals
    """
    try:
        indicators = await data_service.get_technical_indicators()

        # Create summary
        summary = {
            "timestamp": indicators.timestamp,
            "current_price": indicators.current_price,
            "signal": indicators.overall_signal,
            "strength": indicators.overall_strength,
            "indicators_count": len(indicators.indicators),
            "signals": {
                "buy": len([i for i in indicators.indicators if i.signal == "buy"]),
                "sell": len([i for i in indicators.indicators if i.signal == "sell"]),
                "neutral": len([i for i in indicators.indicators if i.signal == "neutral"])
            },
            "recommendation": _get_recommendation(indicators.overall_signal, indicators.overall_strength)
        }

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_recommendation(signal: str, strength: float) -> str:
    """Generate trading recommendation based on signal and strength"""
    if signal == "buy":
        if strength > 0.7:
            return "Strong Buy"
        elif strength > 0.4:
            return "Buy"
        else:
            return "Weak Buy"
    elif signal == "sell":
        if strength > 0.7:
            return "Strong Sell"
        elif strength > 0.4:
            return "Sell"
        else:
            return "Weak Sell"
    else:
        return "Hold"