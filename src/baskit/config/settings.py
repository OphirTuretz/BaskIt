"""Configuration settings for BaskIt."""
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaskItSettings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DB_URL: str = "sqlite:///baskit.db"
    DB_ECHO: bool = False
    
    # Hebrew Text Settings
    MIN_HEBREW_RATIO: float = 0.7
    NORMALIZE_HEBREW: bool = True
    
    # List Settings
    MAX_LISTS_PER_USER: int = 10
    DEFAULT_LIST_NAME: str = "רשימת קניות"
    
    # Item Settings
    DEFAULT_UNIT: str = "יחידה"
    MAX_QUANTITY: int = 99
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[Path] = None
    
    # State Management
    MAX_UNDO_STEPS: int = 50
    UNDO_EXPIRY_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_prefix="BASKIT_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> BaskItSettings:
    """Get cached settings instance."""
    return BaskItSettings() 