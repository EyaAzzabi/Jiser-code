"""Central settings, read from the repo-root .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
LEGAL_DIR = DATA_DIR / "legal"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = ROOT / "models"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
LLM_MODEL = os.getenv("JISER_LLM_MODEL", "claude-sonnet-5").strip()
OFFLINE = os.getenv("JISER_OFFLINE", "0") == "1" or not ANTHROPIC_API_KEY

CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
