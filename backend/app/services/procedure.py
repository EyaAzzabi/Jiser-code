"""CDPF procedure checklist: deterministic, explainable rules (no ML).

Each rule cites its article so the taxpayer, the auditor and the judge can check it.
"""
from __future__ import annotations

from ..domain import (DELAI_AVIS_MIN_JOURS, DROIT_REPRISE_ANS, DUREE_MAX_AUTRES_MOIS,
                      DUREE_MAX_COMPTA_MOIS, PROCEDURE_RULES)
from ..schemas import Notification, ProcedureCheck

_RULES = {r["code"]: r for r in PROCEDURE_RULES}


def _check(code: str, statut: str, detail: str) -> ProcedureCheck:
    r = _RULES[code]
    return ProcedureCheck(code=code, label=r["label"], article=r["article"], statut=statut, detail=detail)


def check_procedure(n: Notification) -> list[ProcedureCheck]:
    out: list[ProcedureCheck] = []
    if n.type_verification == "approfondie":
        if n.date_avis is None:
            out.append(_check("AVIS_PREALABLE", "a_verifier",
                              "La date de l'avis préalable n'apparaît pas dans la notification : demander la copie de l'avis."))
        else:
            out.append(_check("AVIS_PREALABLE", "ok", f"Avis notifié le {n.date_avis:%d/%m/%Y}."))
        if n.date_avis and n.date_debut_verification:
            gap = (n.date_debut_verification - n.date_avis).days
            out.append(_check("DELAI_AVIS_15J", "ok" if gap >= DELAI_AVIS_MIN_JOURS else "vice",
                              f"{gap} jours entre l'avis et le début de la vérification "
                              f"(minimum légal : {DELAI_AVIS_MIN_JOURS} jours)."))
        out.append(_check("MENTION_ASSISTANCE", "ok" if n.mention_assistance else "vice",
                          "Le droit de se faire assister est mentionné." if n.mention_assistance else
                          "Aucune mention du droit de se faire assister par une personne de son choix."))
        if n.date_debut_verification:
            max_m = DUREE_MAX_COMPTA_MOIS if n.comptabilite_conforme else DUREE_MAX_AUTRES_MOIS
            months = (n.date_notification - n.date_debut_verification).days / 30.44
            out.append(_check("DUREE_MAX", "ok" if months <= max_m else "vice",
                              f"Durée de la vérification : {months:.1f} mois, du {n.date_debut_verification:%d/%m/%Y} "
                              f"au {n.date_notification:%d/%m/%Y} (maximum : {max_m} mois "
                              f"{'avec une comptabilité conforme' if n.comptabilite_conforme else 'sans comptabilité admise'})."))
    motives = [c for c in n.chefs if c.motivation_qualite == "absente"]
    out.append(_check("CHEFS_MOTIVES", "ok" if not motives else "vice",
                      "Tous les chefs de redressement sont motivés." if not motives else
                      f"{len(motives)} chef(s) sans motivation : " + ", ".join(c.id for c in motives) + "."))
    out.append(_check("MENTION_DELAI_30J", "ok" if n.mention_delai_30j else "vice",
                      "Le délai de réponse de 30 jours est indiqué." if n.mention_delai_30j else
                      "La notification n'invite pas à répondre dans le délai légal de 30 jours."))
    out.append(_check("PENALITES_INDIQUEES", "ok" if n.penalites_indiquees else "vice",
                      "Les pénalités sont chiffrées." if n.penalites_indiquees else
                      "Les pénalités ne sont pas chiffrées dans la notification."))
    late = [y for y in n.exercices_verifies if n.date_notification.year > y + DROIT_REPRISE_ANS]
    out.append(_check("DROIT_REPRISE", "ok" if not late else "vice",
                      "Tous les exercices sont dans le délai de reprise de 4 ans." if not late else
                      f"Exercice(s) {', '.join(map(str, late))} hors délai de reprise de 4 ans (sauf impôt non déclaré : 10 ans, art. 20)."))
    return out


def vice_codes(n: Notification) -> set[str]:
    # CHEFS_MOTIVES is a per-item weakness, handled by the item-level model, not a file-level defect
    return {c.code for c in check_procedure(n) if c.statut == "vice" and c.code != "CHEFS_MOTIVES"}
