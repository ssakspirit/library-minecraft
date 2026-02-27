"""
Configuration settings for Minecraft Education crawler
"""
import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "minecraft_education.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Crawling settings
BASE_URL = "https://education.minecraft.net"
RESOURCE_URLS = {
    "main": f"{BASE_URL}/ko-kr/resources",
    "lessons": f"{BASE_URL}/ko-kr/resources/explore-lessons",
    "worlds": f"{BASE_URL}/ko-kr/resources/explore-worlds",
    "challenges": f"{BASE_URL}/ko-kr/resources/explore-build-challenges",
}

# Crawler settings
MAX_CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 1.0  # seconds between requests
TIMEOUT = 30000  # milliseconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Database settings
DB_SCHEMA_PATH = BASE_DIR / "schema.sql"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
