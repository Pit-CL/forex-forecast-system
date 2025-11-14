"""Fixed pipeline for 7-day forecaster with real PDF generation"""
import sys
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.forecasting import ForecastEngine
from forex_core.reporting import ChartGenerator, ReportBuilder


def run_forecast_pipeline() -> Path:
    """
    Execute complete 7-day forecast pipeline with real PDF generation.
    
    Returns:
        Path to generated PDF report
    """
    logger.info("Starting 7-day forecast pipeline")
    settings = get_settings()
    
    # 1. Load data
    logger.info("Loading data from providers...")
    loader = DataLoader(settings)
    bundle = loader.load()
    logger.info(f"Data loaded: {len(bundle.indicators)} indicators, {len(bundle.registry.sources)} sources")
    
    # 2. Generate forecast
    logger.info("Generating 7-day forecast...")
    engine = ForecastEngine(settings)
    forecast, artifacts = engine.forecast(bundle)
    logger.info(f"Forecast generated: {len(forecast.series)} points, final mean: {forecast.series[-1].mean:.2f}")
    
    # 3. Generate charts
    logger.info("Creating visualization charts...")
    chart_gen = ChartGenerator(settings)
    charts = chart_gen.generate(bundle, forecast, horizon="7d")
    logger.info(f"Generated {len(charts)} charts")
    
    # 4. Build PDF report
    logger.info("Building PDF report...")
    builder = ReportBuilder(settings)
    artifacts_dict = asdict(artifacts)
    pdf_path = builder.build(bundle, forecast, artifacts_dict, charts, horizon="7d")
    logger.info(f"Report saved: {pdf_path}")
    
    # 5. Log success
    chile_tz = ZoneInfo(settings.report_timezone)
    now = datetime.now(chile_tz)
    logger.success(f"Pipeline completed successfully at {now.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}")
    
    return pdf_path
