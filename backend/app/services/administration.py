"""Administration-side services: file triage, settlement proposals and the steering dashboard."""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache

from ..config import MODELS_DIR
from ..domain import CHEF_TYPES
from ..schemas import Dossier
from . import scoring
from .procedure import check_procedure, vice_codes
from .store import TODAY, OpenFile, get_store


SHORT_LABELS = {
    "TVA_FACTURES_NON_CONFORMES": "TVA irrégulière", "CHARGES_NON_DEDUCTIBLES": "Charges rejetées",
    "MINORATION_CA": "Minoration du CA", "RECONSTITUTION_CA": "Reconstitution du CA",
    "RETENUE_SOURCE_NON_EFFECTUEE": "Retenues à la source", "AVANTAGES_ENTREPRISES_LIEES": "Prix de transfert",
}


def file_summary(f: OpenFile) -> dict:
    d = f.dossier
    n = d.notification
    return {
        "id": d.id, "reference": n.reference, "entreprise": n.entreprise.nom, "gouvernorat": n.entreprise.gouvernorat,
        "taille": n.entreprise.taille, "etape": d.etape, "date_notification": n.date_notification.isoformat(),
        "anciennete_jours": f.age_days, "montant_total": n.montant_total, "montant_recouvrable": round(f.expected, 3),
        "score_solidite": f.score, "priorite": round(f.priority), "vices": f.vices, "groupe": f.groupe,
        "nb_chefs": len(n.chefs),
    }


def triage(limit: int = 100, gouvernorat: str | None = None, etape: str | None = None,
           groupe: str | None = None) -> dict:
    files = list(get_store().open_files.values())
    if gouvernorat:
        files = [f for f in files if f.dossier.notification.entreprise.gouvernorat == gouvernorat]
    if etape:
        files = [f for f in files if f.dossier.etape == etape]
    if groupe:
        files = [f for f in files if f.groupe == groupe]
    files.sort(key=lambda f: f.priority, reverse=True)
    groups: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0})
    for f in files:
        groups[f.groupe]["nb"] += 1
        groups[f.groupe]["montant"] += f.dossier.notification.montant_total
    return {
        "total": len(files),
        "montant_total": round(sum(f.dossier.notification.montant_total for f in files), 3),
        "montant_recouvrable": round(sum(f.expected for f in files), 3),
        "groupes": [{"groupe": k, **v} for k, v in sorted(groups.items(), key=lambda kv: -kv[1]["montant"])],
        "dossiers": [file_summary(f) for f in files[:limit]],
    }


def dossier_detail(dossier_id: str, utilisateur: str | None = None) -> dict | None:
    store = get_store()
    d = store.dossiers.get(dossier_id)
    if d is None:
        return None
    s = scoring.score(d)
    store.log("score_solidite", d.notification.reference, f"Score {s.score_solidite}/100", "modele", utilisateur)
    return {"dossier": d.model_dump(mode="json"), "score": s.model_dump(),
            "procedure": [p.model_dump() for p in check_procedure(d.notification)],
            "conciliation": settlement(d)}


def settlement(d: Dossier) -> dict:
    """Propose an amicable settlement per item, from the model's expected outcome."""
    probas = scoring.chef_probas(d)
    _, shares = scoring.expected_recovery(d, probas)
    has_vice = bool(vice_codes(d.notification))
    items, proposed, expected_total = [], 0.0, 0.0
    for c, p, share in zip(d.notification.chefs, probas, shares):
        total = c.montant_principal + c.penalites
        expected_total += total * share
        if share >= 0.7 and not has_vice:
            action, amount = "maintenir", total
            why = "Chef solide : forte probabilité d'être confirmé."
        elif share >= 0.3:
            action, amount = "transiger", min(c.montant_principal, round(total * min(0.9, share + 0.1), 3))
            why = ("Issue incertaine : proposer le principal (abandon des pénalités) ou un montant réduit, "
                   "dans l'esprit des mesures de réconciliation de la loi de finances 2025.")
        else:
            action, amount = "abandonner", 0.0
            why = "Risque élevé d'annulation (vice de procédure ou motivation insuffisante)."
        proposed += amount
        items.append({"chef_id": c.id, "libelle": c.libelle, "montant": round(total, 3),
                      "p_maintenu": round(float(p[0]), 3), "part_recouvrable": round(float(share), 3),
                      "action": action, "montant_propose": round(amount, 3), "justification": why})
    return {"items": items, "montant_notifie": d.notification.montant_total, "montant_propose": round(proposed, 3),
            "montant_attendu_contentieux": round(expected_total, 3),
            "commentaire": ("Un accord maintenant encaisse le montant proposé tout de suite ; le contentieux rapporterait "
                            "en moyenne le montant attendu, mais après plusieurs années de procédure.")}


MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]


def _monthly_series(dossiers: list[Dossier], today) -> list[dict]:
    """Files notified vs closed per month over the last 12 months."""
    months = []
    y, m = today.year, today.month
    for _ in range(12):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()
    notified = defaultdict(int)
    closed = defaultdict(int)
    for d in dossiers:
        nd = d.notification.date_notification
        notified[(nd.year, nd.month)] += 1
        if d.statut == "cloture":
            closed[(d.date_etape.year, d.date_etape.month)] += 1
    return [{"mois": f"{MOIS[mm - 1]} {str(yy)[2:]}", "notifies": notified[(yy, mm)], "clotures": closed[(yy, mm)]} for yy, mm in months]


@lru_cache(maxsize=32)
def dashboard(zone: str | None = None) -> dict:
    """Aggregates over an immutable store (optionally one governorate): computed once, then cached."""
    store = get_store()
    open_files = [f for f in store.open_files.values() if zone is None or f.dossier.notification.entreprise.gouvernorat == zone]
    closed = [d for d in store.dossiers.values() if d.statut == "cloture" and (zone is None or d.notification.entreprise.gouvernorat == zone)]

    by_gouv: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0, "recouvrable": 0.0})
    by_etape: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0})
    by_type: dict[str, float] = defaultdict(float)
    motifs: dict[str, int] = defaultdict(int)
    for f in open_files:
        n = f.dossier.notification
        g = by_gouv[n.entreprise.gouvernorat]
        g["nb"] += 1
        g["montant"] += n.montant_total
        g["recouvrable"] += f.expected
        by_etape[f.dossier.etape]["nb"] += 1
        by_etape[f.dossier.etape]["montant"] += n.montant_total
        for c in n.chefs:
            by_type[CHEF_TYPES.get(c.type, {}).get("label", c.libelle)] += c.montant_principal + c.penalites
            motifs[SHORT_LABELS.get(c.type, c.libelle)] += 1

    # why do reassessments fail? attribute each cancelled item of a closed file to its main cause
    causes: dict[str, int] = defaultdict(int)
    n_items = n_cancelled = 0
    for d in closed:
        vices = vice_codes(d.notification)
        issues = {i.chef_id: i.issue for i in d.issues}
        for c in d.notification.chefs:
            n_items += 1
            if issues.get(c.id) != "annule":
                continue
            n_cancelled += 1
            if "DROIT_REPRISE" in vices and d.notification.date_notification.year > c.exercice + 4:
                causes["Exercice hors délai de reprise"] += 1
            elif vices:
                causes["Vice de procédure"] += 1
            elif c.motivation_qualite == "absente":
                causes["Chef non motivé"] += 1
            elif c.motivation_qualite == "sommaire":
                causes["Motivation sommaire"] += 1
            else:
                causes["Fond (justificatifs produits)"] += 1

    notified = sum(d.notification.montant_total for d in closed)
    recovered = sum(d.montant_recouvre or 0 for d in closed)
    durations = [(d.date_etape - d.notification.date_notification).days / 30.44 for d in closed]
    metrics_path = MODELS_DIR / "metrics.json"
    return {
        "kpi": {
            "dossiers_en_cours": len(open_files),
            "montant_bloque": round(sum(f.dossier.notification.montant_total for f in open_files), 3),
            "montant_recouvrable_estime": round(sum(f.expected for f in open_files), 3),
            "dossiers_avec_vice": sum(1 for f in open_files if f.vices),
            "taux_recouvrement_historique": round(recovered / notified, 3) if notified else 0,
            "taux_chefs_annules": round(n_cancelled / n_items, 3) if n_items else 0,
            "duree_moyenne_mois": round(sum(durations) / len(durations), 1) if durations else 0,
            "taux_conciliation": round(sum(d.etape.startswith("Conciliation") for d in closed) / len(closed), 3) if closed else 0,
        },
        "par_gouvernorat": [{"gouvernorat": k, **{kk: round(vv, 3) for kk, vv in v.items()}}
                            for k, v in sorted(by_gouv.items(), key=lambda kv: -kv[1]["montant"])],
        "par_etape": [{"etape": k, **v} for k, v in by_etape.items()],
        "par_type": [{"type": k, "montant": round(v, 3)} for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])],
        "causes_annulation": [{"cause": k, "nb": v} for k, v in sorted(causes.items(), key=lambda kv: -kv[1])],
        "motifs": [{"motif": k, "nb": v} for k, v in sorted(motifs.items(), key=lambda kv: -kv[1])],
        "serie_mensuelle": _monthly_series([d for d in store.dossiers.values()
                                            if zone is None or d.notification.entreprise.gouvernorat == zone], TODAY),
        "perimetre": zone or "National",
        "modele": json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None,
    }
