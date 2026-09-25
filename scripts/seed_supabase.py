"""Upload the synthetic dossiers to Supabase (table `dossiers`).

Prerequisites: run supabase/schema.sql in the Supabase SQL editor, and set SUPABASE_URL and
SUPABASE_SERVICE_KEY in .env.

Usage:
    python scripts/seed_supabase.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

BATCH = 300


def main() -> None:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    raw = json.loads((ROOT / "data" / "synthetic" / "dossiers.json").read_text(encoding="utf-8"))
    rows = [{"id": d["id"], "statut": d["statut"], "gouvernorat": d["notification"]["entreprise"]["gouvernorat"],
             "etape": d["etape"], "montant_total": round(sum(c["montant_principal"] + c["penalites"] for c in d["notification"]["chefs"]), 3),
             "data": d} for d in raw]
    for i in range(0, len(rows), BATCH):
        sb.table("dossiers").upsert(rows[i:i + BATCH], on_conflict="id").execute()
        print(f"{min(i + BATCH, len(rows))}/{len(rows)} dossiers uploaded")


if __name__ == "__main__":
    main()
