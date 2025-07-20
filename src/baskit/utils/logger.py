"""Logging configuration for BaskIt using loguru."""
import os
import sys
from pathlib import Path
from loguru import logger

from baskit.config.settings import get_settings

settings = get_settings()

# Remove default handler
logger.remove()

# Define log format based on settings
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> | "
    "<level>{extra}</level>"
) if settings.LOG_FORMAT == "detailed" else (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)

# Ensure logs directory exists
log_dir = Path(settings.LOG_FILE).parent if settings.LOG_FILE else Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Default log file if not set
default_log_file = log_dir / "baskit.log"
log_file = settings.LOG_FILE or default_log_file

# Add console handler with color
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=settings.LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Add file handler with rotation
logger.add(
    log_file,
    format=LOG_FORMAT,
    level=settings.LOG_LEVEL,
    rotation=f"{settings.LOG_ROTATION_SIZE_MB} MB",
    retention=f"{settings.LOG_RETENTION_DAYS} days",
    compression="zip",
    serialize=True,
    backtrace=True,
    diagnose=True,
    enqueue=True,  # Thread-safe logging
)

def get_logger(name: str):
    """Get a logger instance with the given name.
    
    Args:
        name: The name of the module/component requesting the logger.
            Should be the module's __name__ attribute.
            
    Returns:
        A logger instance bound with the given name.
    """
    # Ensure module name starts with baskit.
    if not name.startswith("baskit.") and name != "__main__":
        name = f"baskit.{name}"
    return logger.bind(name=name)

# Export logger instance
logger = get_logger(__name__) 