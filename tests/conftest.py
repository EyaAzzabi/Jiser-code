"""Isolated test setup: in-memory database, no e-mails, no external AI."""
import os
import sys
from pathlib import Path

for var in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "N8N_OTP_WEBHOOK_URL", "N8N_WELCOME_WEBHOOK_URL", "N8N_RAPPEL_WEBHOOK_URL",
            "N8N_NOTIF_WEBHOOK_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ[var] = ""
os.environ["JISER_OFFLINE"] = "1"
os.environ["ADMIN_EMAILS"] = "admin@test.tn"
os.environ["JISER_DATA_KEY"] = "u3Uc-qAi9iiCv3fkBfRUAKrM1gH8w51-nVU8M8A73Jg="

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
