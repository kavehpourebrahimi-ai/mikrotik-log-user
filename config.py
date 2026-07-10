"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "192.168.88.1")
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD", "")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "22"))
MIKROTIK_PEER_HOST = os.getenv("MIKROTIK_PEER_HOST", "")

SYSLOG_HOST = os.getenv("SYSLOG_HOST", "0.0.0.0")
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "514"))
SYSLOG_MAX_LOGS = int(os.getenv("SYSLOG_MAX_LOGS", "50000"))

WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "mikrotik-4d-analyzer-dev-key")

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
