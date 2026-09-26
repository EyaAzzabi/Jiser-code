"""Steering by level of the administration: national (minister), centre (head of centre), team.

* The minister gets aggregates only, with live filters. Any group with fewer than K_ANONYMAT files is
  masked, so no single taxpayer can be recognised from the statistics (tax secrecy).
* The head of centre assigns files to the case officers of the centre and approves settlements
  above the threshold (SEUIL_VALIDATION_CONCILIATION).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ..config import SEUIL_VALIDATION_CONCILIATION
from ..domain import CHEF_TYPES
from .administration import SHORT_LABELS, settlement
from .db import repo
from .permissions import centre_de, perimetre
from .store import TODAY, get_store

K_ANONYMAT = 5
TRANCHES = {"petit": (0, 100_000), "moyen": (100_000, 1_000_000), "gros": (1_000_000, float("inf"))}


def _motif(d) -> str:
    top = max(d.notification.chefs, key=lambda c: c.montant_principal + c.penalites)
    return SHORT_LABELS.get(top.type, CHEF_TYPES.get(top.type, {}).get("label", top.libelle))


def _garde(d, f: dict) -> bool:
    n = d.notification
    if f.get("gouvernorats") and n.entreprise.gouvernorat not in f["gouvernorats"]:
        return False
    if f.get("motifs") and _motif(d) not in f["motifs"]:
        return False
    if f.get("etape") and d.etape != f["etape"]:
        return False
    if f.get("tranche") in TRANCHES:
        lo, hi = TRANCHES[f["tranche"]]
        if not lo <= n.montant_total < hi:
            return False
    if f.get("periode_mois"):
        if n.date_notification < TODAY - timedelta(days=int(f["periode_mois"]) * 30.44):
            return False
    return True


def _masquer(rows: list[dict], cles: tuple[str, ...]) -> list[dict]:
    """k-anonymity: small groups are hidden (their numbers could point to one company)."""
    return [r if r["nb"] >= K_ANONYMAT else {**{k: r[k] for k in r if k not in cles}, **{k: None for k in cles}, "masque": True}
            for r in rows]


def national(filtres: dict) -> dict:
    store = get_store()
    ouverts = [f for f in store.open_files.values() if _garde(f.dossier, filtres)]
    clos = [d for d in store.dossiers.values() if d.statut == "cloture" and _garde(d, filtres)]

    par_g: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0, "recouvrable": 0.0})
    par_m: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0})
    par_e: dict[str, dict] = defaultdict(lambda: {"nb": 0, "montant": 0.0})
    for f in ouverts:
        n = f.dossier.notification
        g = par_g[n.entreprise.gouvernorat]
        g["nb"] += 1; g["montant"] += n.montant_total; g["recouvrable"] += f.expected
        m = par_m[_motif(f.dossier)]
        m["nb"] += 1; m["montant"] += n.montant_total
        e = par_e[f.dossier.etape]
        e["nb"] += 1; e["montant"] += n.montant_total

    notifie = sum(d.notification.montant_total for d in clos)
    recouvre = sum(d.montant_recouvre or 0 for d in clos)
    items = [i for d in clos for i in d.issues]
    durees = [(d.date_etape - d.notification.date_notification).days / 30.44 for d in clos]

    # monthly flow over the period (at least 12 months)
    mois = []
    y, mm = TODAY.year, TODAY.month
    for _ in range(max(12, int(filtres.get("periode_mois") or 12))):
        mois.append((y, mm))
        y, mm = (y, mm - 1) if mm > 1 else (y - 1, 12)
    mois.reverse()
    entrees, sorties = defaultdict(int), defaultdict(int)
    for d in store.dossiers.values():
        if not _garde(d, {**filtres, "periode_mois": None}):
            continue
        nd = d.notification.date_notification
        entrees[(nd.year, nd.month)] += 1
        if d.statut == "cloture":
            sorties[(d.date_etape.year, d.date_etape.month)] += 1
    NOMS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

    r3 = lambda v: round(v, 3)
    return {
        "kpi": {
            "dossiers_en_cours": len(ouverts),
            "montant_bloque": r3(sum(f.dossier.notification.montant_total for f in ouverts)),
            "montant_recouvrable": r3(sum(f.expected for f in ouverts)),
            "dossiers_avec_vice": sum(1 for f in ouverts if f.vices),
            "taux_recouvrement": round(recouvre / notifie, 3) if notifie else None,
            "taux_annulation": round(sum(i.issue == "annule" for i in items) / len(items), 3) if items else None,
            "taux_conciliation": round(sum(d.etape.startswith("Conciliation") for d in clos) / len(clos), 3) if clos else None,
            "duree_moyenne_mois": round(sum(durees) / len(durees), 1) if durees else None,
            "dossiers_clos": len(clos),
        },
        "par_gouvernorat": _masquer(sorted(({"gouvernorat": k, "nb": v["nb"], "montant": r3(v["montant"]), "recouvrable": r3(v["recouvrable"])}
                                            for k, v in par_g.items()), key=lambda r: -r["montant"]), ("nb", "montant", "recouvrable")),
        "par_motif": _masquer(sorted(({"motif": k, "nb": v["nb"], "montant": r3(v["montant"])} for k, v in par_m.items()),
                                     key=lambda r: -r["montant"]), ("nb", "montant")),
        "par_etape": _masquer([{"etape": k, "nb": v["nb"], "montant": r3(v["montant"])} for k, v in par_e.items()], ("nb", "montant")),
        "flux_mensuel": [{"mois": f"{NOMS[m - 1]} {str(a)[2:]}", "entrees": entrees[(a, m)], "sorties": sorties[(a, m)]} for a, m in mois],
        "activite": activite_temps_reel(),
        "k_anonymat": K_ANONYMAT,
        "options": {"gouvernorats": sorted({f.dossier.notification.entreprise.gouvernorat for f in store.open_files.values()}),
                    "motifs": sorted(set(SHORT_LABELS.values())),
                    "etapes": sorted({f.dossier.etape for f in store.open_files.values()})},
        "genere_le": datetime.now(timezone.utc).isoformat(),
    }


def activite_temps_reel() -> dict:
    """Live platform activity (from the audit journal): what happened in the last 24 hours."""
    depuis = datetime.now(timezone.utc) - timedelta(hours=24)
    compte: dict[str, int] = defaultdict(int)
    for j in repo().journal_list(500):
        try:
            t = datetime.fromisoformat(str(j["horodatage"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if t >= depuis:
            compte[j["action"]] += 1
    return {"analyses": compte["analyse_notification"], "reponses": compte["brouillon_reponse"],
            "messages": compte["message"], "conciliations": compte["decision_conciliation"] + compte["proposition_conciliation"],
            "questions_ia": compte["assistant"], "total": sum(compte.values())}


# ---- head of centre: team and assignments -----------------------------------------------------

def equipe(chef: dict) -> list[dict]:
    centre = centre_de(chef)
    affect = repo().affectations_all()
    store = get_store()
    out = []
    for u in repo().list_users():
        full = repo().get_user(u["email"]) or u
        if full["role"] != "contentieux" or (full.get("statut") or "actif") != "actif" or centre_de(full) != centre:
            continue
        mes = [a for a in affect.values() if a.get("agent_id") == full["id"] and a["dossier_id"] in store.open_files]
        out.append({"id": full["id"], "nom": f"{full['prenom']} {full['nom']}", "email": full["email"],
                    "dossiers": len(mes), "montant": round(sum(store.open_files[a["dossier_id"]].dossier.notification.montant_total for a in mes), 3)})
    return sorted(out, key=lambda a: a["nom"])


def affecter(chef: dict, dossier_id: str, agent_id: str, chef_email: str) -> dict:
    store = get_store()
    f = store.open_files.get(dossier_id)
    if f is None:
        raise LookupError("Dossier introuvable")
    zone = perimetre(chef)
    if zone and f.dossier.notification.entreprise.gouvernorat != zone:
        raise PermissionError("Ce dossier n'appartient pas à votre centre.")
    agent = repo().get_user_by_id(agent_id)
    if not agent or agent["role"] != "contentieux" or centre_de(agent) != centre_de(chef):
        raise PermissionError("Cet agent n'appartient pas à votre centre.")
    repo().affectation_set({"dossier_id": dossier_id, "agent_id": agent_id, "agent_nom": f"{agent['prenom']} {agent['nom']}", "par": chef_email})
    repo().journal_add({"action": "affectation", "cible": f.dossier.notification.reference, "recommandation": f"Affecté à {agent['prenom']} {agent['nom']}",
                        "mode": "humain", "decision_humaine": "validée", "utilisateur": chef_email})
    return {"ok": True}


# ---- settlements: proposal, then approval above the threshold ----------------------------------

def proposer_conciliation(session: dict, dossier_id: str) -> dict:
    store = get_store()
    d = store.dossiers.get(dossier_id)
    if d is None:
        raise LookupError("Dossier introuvable")
    c = settlement(d)
    ref = d.notification.reference
    if session["role"] == "contentieux" and c["montant_propose"] > SEUIL_VALIDATION_CONCILIATION:
        repo().conciliation_add({"dossier_id": dossier_id, "reference": ref, "gouvernorat": d.notification.entreprise.gouvernorat,
                                 "montant_notifie": d.notification.montant_total, "montant_propose": c["montant_propose"],
                                 "propose_par": session["email"], "statut": "en_attente"})
        repo().journal_add({"action": "proposition_conciliation", "cible": ref, "recommandation": "Proposition de conciliation",
                            "mode": "humain", "decision_humaine": "en attente de validation du chef de centre", "utilisateur": session["email"]})
        return {"ok": True, "statut": "en_attente_validation",
                "message": f"Montant supérieur à {SEUIL_VALIDATION_CONCILIATION:,.0f} DT : proposition transmise au chef de centre pour validation.".replace(",", " ")}
    repo().journal_add({"action": "decision_conciliation", "cible": ref, "recommandation": "Proposition de conciliation", "mode": "humain",
                        "decision_humaine": "validée", "utilisateur": session["email"]})
    return {"ok": True, "statut": "validee", "message": "Proposition de conciliation validée."}


def conciliations_a_valider(chef: dict) -> list[dict]:
    zone = perimetre(chef)
    return [c for c in repo().conciliations_list() if c["statut"] == "en_attente" and (zone is None or c["gouvernorat"] == zone)]


def decider_conciliation(chef: dict, chef_email: str, cid: str, decision: str, motif: str = "") -> dict:
    c = next((x for x in repo().conciliations_list() if x["id"] == cid), None)
    if c is None or c["statut"] != "en_attente":
        raise LookupError("Proposition introuvable ou déjà traitée.")
    zone = perimetre(chef)
    if zone and c["gouvernorat"] != zone:
        raise PermissionError("Cette proposition ne relève pas de votre centre.")
    statut = "validee" if decision == "validee" else "refusee"
    repo().conciliation_update(cid, statut=statut, decide_par=chef_email, motif=motif, decide_le=datetime.now(timezone.utc).isoformat())
    repo().journal_add({"action": "decision_conciliation", "cible": c["reference"], "recommandation": "Validation du chef de centre",
                        "mode": "humain", "decision_humaine": "validée" if statut == "validee" else f"refusée {motif}".strip(),
                        "utilisateur": chef_email})
    return {"ok": True, "statut": statut}
