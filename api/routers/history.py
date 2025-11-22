from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_DIR = Path("/app/output/forecasts/history")

@router.get("/dates")
async def get_available_dates():
    if not HISTORY_DIR.exists():
        return {"dates": []}
    
    dates = [d.name for d in sorted(HISTORY_DIR.glob("*")) if d.is_dir()]
    return {"dates": dates, "count": len(dates)}

@router.get("/{date}/{horizon}")
async def get_historical_forecast(date: str, horizon: str):
    forecast_file = HISTORY_DIR / date / f"forecast_{horizon}.json"
    
    if not forecast_file.exists():
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    with open(forecast_file, 'r') as f:
        return json.load(f)
