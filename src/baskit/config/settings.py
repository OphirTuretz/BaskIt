"""Configuration settings for BaskIt."""
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Default log directory
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "baskit.log"

class OpenAISettings(BaseSettings):
    """OpenAI-specific settings."""
    API_KEY: str = "your_api_key_here"
    MODEL: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.0  # Zero temperature for maximum confidence and deterministic responses
    MAX_RETRIES: int = 3
    TIMEOUT: int = 10
    MAX_TOKENS: int = 150

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        case_sensitive=False,
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @validator("TEMPERATURE")
    def validate_temperature(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v

    @validator("API_KEY")
    def validate_api_key(cls, v: str) -> str:
        if v == "your_api_key_here":
            raise ValueError("OpenAI API key not configured")
        return v


class BaskItSettings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DB_URL: str = "sqlite:///baskit.db"
    DB_ECHO: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[Path] = DEFAULT_LOG_FILE
    LOG_FORMAT: str = "detailed"  # simple, detailed
    LOG_RETENTION_DAYS: int = 7
    LOG_ROTATION_SIZE_MB: int = 1  # Changed from 10 to 1
    
    # AI Feature Flags
    USE_MOCK_AI: bool = True
    ENABLE_CONTEXT: bool = True
    CONTEXT_MAX_TURNS: int = 10
    
    # Hebrew Text Settings
    MIN_HEBREW_RATIO: float = 0.7
    NORMALIZE_HEBREW: bool = True
    
    # List Settings
    MAX_LISTS_PER_USER: int = 10
    DEFAULT_LIST_NAME: str = "רשימת קניות"
    SOFT_DELETE: bool = True
    
    # Item Settings
    DEFAULT_UNIT: str = "יחידה"
    MAX_QUANTITY: int = 99
    ALLOW_DUPLICATE_ITEMS: bool = False
    AUTO_MERGE_SIMILAR: bool = True
    
    # Tool Settings
    TOOL_CONFIDENCE_THRESHOLD: float = 0.6  # Lowered from 0.8 to better match actual confidence scores
    TOOL_TIMEOUT: int = 5
    
    # Error Handling
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1
    
    # Application Settings
    ENABLE_RTL: bool = True
    DEFAULT_LANGUAGE: str = "he"
    TIMEZONE: str = "Asia/Jerusalem"
    
    # State Management (deprecated)
    MAX_UNDO_STEPS: int = 50
    UNDO_EXPIRY_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_prefix="BASKIT_",
        case_sensitive=False,
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert relative DB path to absolute path from project root
        if self.DB_URL.startswith("sqlite:///"):
            relative_path = self.DB_URL.replace("sqlite:///", "")
            absolute_path = PROJECT_ROOT / relative_path
            self.DB_URL = f"sqlite:///{absolute_path}"
        
        # Ensure log file path is absolute and parent directory exists
        if self.LOG_FILE:
            if not self.LOG_FILE.is_absolute():
                self.LOG_FILE = PROJECT_ROOT / self.LOG_FILE
            self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v

    @validator("LOG_FORMAT")
    def validate_log_format(cls, v: str) -> str:
        valid_formats = ["simple", "detailed"]
        v = v.lower()
        if v not in valid_formats:
            raise ValueError(f"Log format must be one of: {', '.join(valid_formats)}")
        return v

    @validator("TOOL_CONFIDENCE_THRESHOLD")
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v

    @validator("MIN_HEBREW_RATIO")
    def validate_hebrew_ratio(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Hebrew ratio must be between 0 and 1")
        return v


class StreamlitSettings(BaseSettings):
    """Streamlit-specific settings."""
    THEME: str = "light"
    SERVER_PORT: int = 8501
    BROWSER_GATHER_USAGE_STATS: bool = False
    THEME_PRIMARY_COLOR: str = "#FF4B4B"
    THEME_BACKGROUND_COLOR: str = "#FFFFFF"
    THEME_TEXT_COLOR: str = "#262730"
    THEME_FONT: str = "sans-serif"

    model_config = SettingsConfigDict(
        env_prefix="STREAMLIT_",
        case_sensitive=False
    )

    @validator("THEME")
    def validate_theme(cls, v: str) -> str:
        valid_themes = ["light", "dark"]
        if v not in valid_themes:
            raise ValueError(f"Theme must be one of: {', '.join(valid_themes)}")
        return v


@lru_cache()
def get_settings() -> BaskItSettings:
    """Get cached settings instance."""
    return BaskItSettings()


@lru_cache()
def get_openai_settings() -> OpenAISettings:
    """Get cached OpenAI settings instance."""
    return OpenAISettings()


@lru_cache()
def get_streamlit_settings() -> StreamlitSettings:
    """Get cached Streamlit settings instance."""
    return StreamlitSettings()


def clear_settings_cache() -> None:
    """Clear all settings caches to force reload from environment."""
    get_settings.cache_clear()
    get_openai_settings.cache_clear()
    get_streamlit_settings.cache_clear() 