"""
Market drivers router for API endpoints
"""
from fastapi import APIRouter, HTTPException

from models import DriversResponse
from services.data_service import DataService

router = APIRouter(prefix="/api/drivers", tags=["drivers"])
data_service = DataService()


@router.get("", response_model=DriversResponse)
async def get_market_drivers():
    """
    Get current market drivers affecting USD/CLP

    Returns key market drivers including:
    - Copper prices
    - US Dollar Index (DXY)
    - Chilean and US bond yields
    - Oil prices
    - Correlation and impact analysis
    """
    try:
        drivers = await data_service.get_market_drivers()
        return drivers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_drivers_summary():
    """
    Get summarized market drivers analysis

    Returns aggregated impact and key drivers
    """
    try:
        drivers = await data_service.get_market_drivers()

        # Calculate aggregate impact
        positive_drivers = [d for d in drivers.drivers if d.impact == "positive"]
        negative_drivers = [d for d in drivers.drivers if d.impact == "negative"]
        neutral_drivers = [d for d in drivers.drivers if d.impact == "neutral"]

        # Find strongest correlations
        sorted_drivers = sorted(drivers.drivers, key=lambda x: abs(x.correlation), reverse=True)

        summary = {
            "timestamp": drivers.timestamp,
            "total_drivers": len(drivers.drivers),
            "impact_summary": {
                "positive": len(positive_drivers),
                "negative": len(negative_drivers),
                "neutral": len(neutral_drivers)
            },
            "strongest_correlations": [
                {
                    "name": d.name,
                    "correlation": d.correlation,
                    "current_impact": d.impact
                }
                for d in sorted_drivers[:3]
            ],
            "market_outlook": _determine_outlook(positive_drivers, negative_drivers),
            "key_driver": sorted_drivers[0].name if sorted_drivers else None
        }

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _determine_outlook(positive_drivers, negative_drivers) -> str:
    """Determine overall market outlook based on driver impacts"""
    if len(positive_drivers) > len(negative_drivers) + 1:
        return "Bullish for CLP"
    elif len(negative_drivers) > len(positive_drivers) + 1:
        return "Bearish for CLP"
    else:
        return "Mixed signals"