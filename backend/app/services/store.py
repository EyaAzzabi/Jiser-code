"""Dossier store: contentious files (Supabase or local file), precomputed scores, AI journal access.

Dossiers are loaded once at startup; the journal is read and written through the repository (db.py).
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from ..config import SYNTHETIC_DIR
from ..domain import CHEF_TYPES
from ..schemas import Dossier
from . import scoring
from .db import repo
from .procedure import vice_codes

TODAY = date.today()   # deadlines and ages are computed against the real date


@dataclass
class OpenFile:
    dossier: Dossier
    expected: float
    score: int
    priority: float
    age_days: int
    vices: list[str]
    groupe: str


@dataclass
class Store:
    dossiers: dict[str, Dossier]
    open_files: dict[str, OpenFile]

    def log(self, action: str, cible: str, recommandation: str, mode: str = "modele", utilisateur: str | None = None) -> None:
        repo().journal_add({"action": action, "cible": cible, "recommandation": recommandation, "mode": mode,
                            "utilisateur": utilisateur})

    @property
    def journal(self) -> list[dict]:
        return repo().journal_list(200)


def _dominant_type(d: Dossier) -> str:
    top = max(d.notification.chefs, key=lambda c: c.montant_principal + c.penalites)
    return CHEF_TYPES.get(top.type, {}).get("label", top.libelle)


_verrou = threading.Lock()


def get_store() -> Store:
    """Loaded once; the lock stops a request and the startup thread from loading it twice at the same time."""
    with _verrou:
        return _charger_store()


@lru_cache(maxsize=1)
def _charger_store() -> Store:
    # dossiers live in Supabase when configured (seeded by scripts/seed_supabase.py), else the local file
    raw = repo().dossiers_all() or json.loads((SYNTHETIC_DIR / "dossiers.json").read_text(encoding="utf-8"))
    dossiers = {d["id"]: Dossier.model_validate(d) for d in raw}
    open_files = {}
    for d in dossiers.values():
        if d.statut != "en_cours":
            continue
        expected, _ = scoring.expected_recovery(d)
        total = d.notification.montant_total or 1.0
        age = (TODAY - d.notification.date_notification).days
        # recover the most money first; older files get a boost (time erodes recovery)
        priority = expected * (1 + 0.25 * min(age / 365, 2))
        open_files[d.id] = OpenFile(dossier=d, expected=expected, score=int(round(100 * expected / total)),
                                    priority=priority, age_days=age, vices=sorted(vice_codes(d.notification)),
                                    groupe=_dominant_type(d))
    return Store(dossiers=dossiers, open_files=open_files)
