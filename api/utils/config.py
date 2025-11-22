"""
Configuration module for the Forex Forecast API
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    api_title: str = Field(default="Forex Forecast System API")
    api_version: str = Field(default="1.0.0")
    api_description: str = Field(default="API for USD/CLP forex forecasting dashboard")

    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)

    # Data Paths (production)
    data_path: Path = Field(default=Path("/app/data"))
    output_path: Path = Field(default=Path("/app/output"))
    warehouse_path: Path = Field(default=Path("/app/data/warehouse"))

    # Development mode
    development_mode: bool = Field(default=True)

    # CORS Configuration
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:5173", "*"])
    cors_credentials: bool = Field(default=True)
    cors_methods: List[str] = Field(default=["*"])
    cors_headers: List[str] = Field(default=["*"])

    # Cache Configuration
    cache_ttl: int = Field(default=300)  # 5 minutes

    # News API Configuration (optional)
    news_api_key: Optional[str] = Field(default=None)

    # Logging
    log_level: str = Field(default="INFO")
    slack_webhook_url: str = Field(default="")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override paths if in development mode
        if self.development_mode:
            base_path = Path("/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system")
            self.data_path = base_path / "api" / "mock_data"
            self.output_path = base_path / "api" / "mock_data" / "output"
            self.warehouse_path = base_path / "api" / "mock_data" / "warehouse"


# Create global settings instance
settings = Settings()


# Ensure directories exist in development
if settings.development_mode:
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    settings.warehouse_path.mkdir(parents=True, exist_ok=True)