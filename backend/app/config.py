"""
Configuration management for SEO Analysis API
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/seo_analysis",
        alias="DATABASE_URL"
    )

    # API Keys
    pagespeed_api_key: Optional[str] = Field(default=None, alias="PAGESPEED_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Google Search Console
    gsc_credentials_path: Optional[str] = Field(default=None, alias="GSC_CREDENTIALS_PATH")

    # Application
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], alias="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def load_thresholds(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load thresholds configuration from YAML file"""
    if config_path is None:
        # Default path relative to this file
        config_path = Path(__file__).parent.parent / "config" / "thresholds.yml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


@lru_cache()
def get_thresholds() -> Dict[str, Any]:
    """Get cached thresholds configuration"""
    return load_thresholds()
