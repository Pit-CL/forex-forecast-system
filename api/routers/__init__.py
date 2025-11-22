from .forecasts import router as forecasts_router
from .indicators import router as indicators_router
from .news import router as news_router
from .drivers import router as drivers_router
from .market import router as market_router
from .history import router as history_router
from .market_indicators import router as market_indicators_router

__all__ = [
    "forecasts_router",
    "indicators_router",
    "news_router",
    "drivers_router",
    "market_router",
    "history_router",
    "market_indicators_router"
]
