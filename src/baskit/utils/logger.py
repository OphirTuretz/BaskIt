"""Logging configuration for BaskIt using loguru."""
import os
import sys
from loguru import logger

from baskit.config.settings import get_settings

settings = get_settings()

# Remove default handler
logger.remove()

# Add console handler with color
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> | <level>{extra}</level>",
    level=os.getenv("LOG_LEVEL", settings.LOG_LEVEL),
    colorize=True,
    serialize=True,
)

# Add file handler with rotation
if settings.LOG_FILE:
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message} | {extra}",
        level=os.getenv("LOG_LEVEL", settings.LOG_LEVEL),
        rotation="10 MB",
        retention="1 week",
        compression="zip",
        serialize=True,
    )

def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name) 