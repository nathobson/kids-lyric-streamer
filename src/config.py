"""Configuration management for lyrics display."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "cache"
FONTS_DIR = BASE_DIR / "fonts"
CONFIG_FILE = BASE_DIR / "config.json"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
FONTS_DIR.mkdir(exist_ok=True)

# ACRCloud settings
ACRCLOUD_HOST = os.getenv("ACRCLOUD_HOST", "identify-eu-west-1.acrcloud.com")
ACRCLOUD_ACCESS_KEY = os.getenv("ACRCLOUD_ACCESS_KEY", "")
ACRCLOUD_ACCESS_SECRET = os.getenv("ACRCLOUD_ACCESS_SECRET", "")

# Audio settings (optimized for Pi Zero)
SAMPLE_RATE = 16000  # 16kHz - sufficient for fingerprinting, lower CPU
CHANNELS = 1  # Mono
RECORD_SECONDS = 5  # Duration of audio sample for recognition

# Recognition settings
RECOGNITION_INTERVAL = int(os.getenv("RECOGNITION_INTERVAL", "45"))  # Seconds between recognitions

# Display settings
DISPLAY_FPS = 30
BACKGROUND_COLOR = (0, 0, 0)  # Black
TEXT_COLOR = (255, 255, 255)  # White
DIM_TEXT_COLOR = (100, 100, 100)  # Gray for context lines
FONT_SIZE_LARGE = 48  # Current lyric
FONT_SIZE_SMALL = 24  # Context lyrics and now playing

# User preferences (persisted to config.json)
_user_config = {}


def load_user_config():
    """Load user preferences from config.json."""
    global _user_config
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                _user_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            _user_config = {}
    return _user_config


def save_user_config():
    """Save user preferences to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(_user_config, f, indent=2)


def get_time_offset() -> int:
    """Get manual time offset in milliseconds."""
    load_user_config()
    return _user_config.get("time_offset_ms", int(os.getenv("TIME_OFFSET_MS", "0")))


def set_time_offset(offset_ms: int):
    """Set manual time offset in milliseconds."""
    _user_config["time_offset_ms"] = offset_ms
    save_user_config()


def adjust_time_offset(delta_ms: int) -> int:
    """Adjust time offset by delta and return new value."""
    current = get_time_offset()
    new_offset = current + delta_ms
    set_time_offset(new_offset)
    return new_offset

