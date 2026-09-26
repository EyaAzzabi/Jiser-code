"""Deadline reminders by e-mail (through the n8n "jiser-rappel" webhook).

* When a notification is analysed: an "échéance enregistrée" e-mail with the reply deadline.
* Then reminders at J-15, J-7, J-3 and J-1, each sent once per analysis (deduplicated through the
  audit journal, so a restart never re-sends).
A background thread checks every few hours; admins can also trigger a run from /plateforme.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date

from ..config import APP_URL, N8N_RAPPEL_WEBHOOK_URL
from .auth import _post_n8n, mask
from .db import repo

log = logging.getLogger("jiser.rappels")

PALIERS = [15, 7, 3, 1]
CHECK_EVERY_S = 6 * 3600
ACTION = "rappel_email"


def _palier(jours: int) -> int | None:
    """The tightest reminder step reached: 20 days left -> none, 12 -> J-15, 2 -> J-3."""
    reached = [p for p in PALIERS if jours <= p]
    return min(reached) if reached else None


def _send(row: dict, palier: str) -> bool:
    if not N8N_RAPPEL_WEBHOOK_URL:
        log.info("reminder %s for %s not sent: N8N_RAPPEL_WEBHOOK_URL not set", palier, mask(row["email"]))
        return False
    d = date.fromisoformat(str(row["date_limite"]))
    ok = _post_n8n(N8N_RAPPEL_WEBHOOK_URL, {
        "email": row["email"], "prenom": row["prenom"], "reference": row["reference"], "entreprise": row["entreprise"],
        "date_limite": d.strftime("%d/%m/%Y"), "jours_restants": row["jours_restants"], "palier": palier,
        "lien": f"{APP_URL}/entreprise/dossiers/{row['id']}"})
    if ok:
        repo().journal_add({"action": ACTION, "cible": f"{row['id']}:{palier}",
                            "recommandation": f"Rappel {palier} envoyé ({row['reference']}, échéance {d:%d/%m/%Y})",
                            "mode": "automatique", "decision_humaine": "sans objet", "utilisateur": row["email"]})
    return ok


def echeance_enregistree(analyse_row: dict, user: dict) -> None:
    """Right after an analysis is saved: tell the user their deadline (in a thread: never blocks the request)."""
    jours = (date.fromisoformat(str(analyse_row["date_limite"])) - date.today()).days
    if jours < 0:
        return
    row = {**analyse_row, "email": user["email"], "prenom": user["prenom"], "jours_restants": jours}
    threading.Thread(target=_send, args=(row, "enregistrement"), daemon=True).start()


def envoyer_rappels() -> dict:
    """Send every reminder due now. Returns counts for the admin screen."""
    sent = skipped = 0
    db = repo()
    for row in db.upcoming_deadlines(max(PALIERS)):
        p = _palier(row["jours_restants"])
        if p is None:
            continue
        palier = f"J-{p}"
        if db.journal_has(ACTION, f"{row['id']}:{palier}"):
            skipped += 1
            continue
        sent += _send(row, palier)
    log.info("reminders: %s sent, %s already sent", sent, skipped)
    return {"envoyes": sent, "deja_envoyes": skipped, "webhook": bool(N8N_RAPPEL_WEBHOOK_URL)}


def demarrer_planificateur() -> None:
    def loop():
        time.sleep(30)   # let the API finish starting
        while True:
            try:
                envoyer_rappels()
            except Exception as e:  # a failed run must not kill the thread
                log.error("reminder run failed: %s", e)
            time.sleep(CHECK_EVERY_S)
    threading.Thread(target=loop, daemon=True, name="rappels").start()
