"""In-memory store for the prototype: synthetic dossiers, precomputed scores and the AI journal.

Production would use PostgreSQL; the API layer does not depend on this module's internals.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache

from ..config import SYNTHETIC_DIR
from ..domain import CHEF_TYPES
from ..schemas import Dossier
from . import scoring
from .procedure import vice_codes

TODAY = date(2026, 9, 25)   # fixed "today" of the demo so ages and deadlines are stable


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
    journal: list[dict]

    def log(self, action: str, cible: str, recommandation: str, mode: str = "modele") -> None:
        self.journal.insert(0, {"horodatage": datetime.now().isoformat(timespec="seconds"), "action": action,
                                "cible": cible, "recommandation": recommandation, "mode": mode,
                                "decision_humaine": "en attente"})
        del self.journal[500:]


def _dominant_type(d: Dossier) -> str:
    top = max(d.notification.chefs, key=lambda c: c.montant_principal + c.penalites)
    return CHEF_TYPES.get(top.type, {}).get("label", top.libelle)


@lru_cache(maxsize=1)
def get_store() -> Store:
    raw = json.loads((SYNTHETIC_DIR / "dossiers.json").read_text(encoding="utf-8"))
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
    return Store(dossiers=dossiers, open_files=open_files, journal=[])
