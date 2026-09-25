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


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# --- LLM ------------------------------------------------------------------------------------
# Gemini (Google AI Studio) has a permanent free tier; Claude is kept as an option.
GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_MODEL = _env("GEMINI_MODEL")            # empty = pick the best available Flash model
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _env("JISER_LLM_MODEL", "claude-sonnet-5")
LLM_PROVIDER = _env("JISER_LLM_PROVIDER") or ("gemini" if GEMINI_API_KEY else "anthropic" if ANTHROPIC_API_KEY else "none")
OFFLINE = _env("JISER_OFFLINE", "0") == "1" or LLM_PROVIDER == "none"

# --- Database (Supabase) --------------------------------------------------------------------
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY")   # server-side only, never sent to the browser

# --- n8n (e-mail automation) ----------------------------------------------------------------
N8N_OTP_WEBHOOK_URL = _env("N8N_OTP_WEBHOOK_URL")
N8N_WELCOME_WEBHOOK_URL = _env("N8N_WELCOME_WEBHOOK_URL")
N8N_SHARED_SECRET = _env("N8N_SHARED_SECRET")        # sent as X-Jiser-Secret, checked by n8n and by /api/n8n/*

# --- Access control -------------------------------------------------------------------------
ADMIN_EMAILS = {e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()}
APP_URL = _env("APP_URL", "http://localhost:5173")

CORS_ORIGINS = [APP_URL, "http://localhost:5173", "http://127.0.0.1:5173"]
