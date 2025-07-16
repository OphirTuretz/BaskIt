"""Configuration management for BaskIt."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)

# App settings
USE_MOCK_APIS = os.getenv("USE_MOCK_APIS", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "baskit.log")) 