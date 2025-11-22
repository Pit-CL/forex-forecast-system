"""Routers module"""
from .forecasts import router as forecasts_router
from .indicators import router as indicators_router
from .news import router as news_router
from .drivers import router as drivers_router

__all__ = [
    "forecasts_router",
    "indicators_router",
    "news_router",
    "drivers_router"
]