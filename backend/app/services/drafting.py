"""Draft the taxpayer's written reply (opposition) to a notification — art. 44 CDPF.

The offline template is complete and usable; Claude, when available, rewrites it into a
more fluent letter without adding facts. Either way the draft must be reviewed by a professional.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from ..schemas import AnalyseNotification
from . import llm
from .letter import fmt_dt


def _template(a: AnalyseNotification, signataire: str) -> str:
    n = a.notification
    vices = [p for p in a.procedure if p.statut == "vice" and p.code != "CHEFS_MOTIVES"]
    lines = [
        n.entreprise.nom,
        f"Matricule fiscal : {n.entreprise.matricule_fiscal}",
        "",
        f"À l'attention de Monsieur le Chef du {n.centre}",
        "",
        f"{n.entreprise.gouvernorat}, le {date.today():%d/%m/%Y}",
        "",
        f"Objet : Opposition aux résultats de la vérification fiscale — notification réf. {n.reference} "
        f"du {n.date_notification:%d/%m/%Y}",
        "",
        "Monsieur le Chef de centre,",
        "",
        "Conformément à l'article 44 du Code des droits et procédures fiscaux (CDPF), nous avons l'honneur de "
        "formuler, dans le délai légal de quarante-cinq jours, nos observations, oppositions et réserves sur les résultats "
        "de la vérification qui nous ont été notifiés.",
    ]
    if vices:
        lines += ["", "I. Sur la régularité de la procédure", ""]
        for v in vices:
            lines.append(f"- {v.detail} Ce manquement méconnaît l'article {v.article.replace('cdpf-art-', '')} du CDPF. "
                         "Nous demandons en conséquence l'annulation des redressements fondés sur cette procédure.")
    lines += ["", f"{'II' if vices else 'I'}. Sur le fond, chef par chef", ""]
    for ca in a.chefs:
        c = ca.chef
        lines.append(f"Chef {c.id} — {c.libelle} (exercice {c.exercice}, {fmt_dt(c.montant_principal + c.penalites)})")
        for arg in ca.arguments:
            if not arg.startswith("Vice de procédure"):
                lines.append(f"- {arg}")
        if ca.contestabilite == "solide":
            lines.append("- Nous nous réservons le droit de produire des éléments complémentaires sur ce point.")
        lines.append("- Pièces jointes : " + "; ".join(ca.pieces_a_fournir) + ".")
        lines.append("")
    lines += [
        "Pour l'ensemble de ces raisons, nous vous prions de bien vouloir réexaminer les résultats de la vérification, "
        "et restons à votre disposition pour toute discussion, assistés le cas échéant du conseil de notre choix "
        "(article 42 du CDPF).",
        "",
        "Veuillez agréer, Monsieur le Chef de centre, l'expression de notre haute considération.",
        "",
        signataire,
        "",
        "— Brouillon généré par JISER : à relire et compléter par un professionnel avant envoi. —",
    ]
    return "\n".join(lines)


class _Draft(BaseModel):
    lettre: str


def draft_reply(a: AnalyseNotification, signataire: str = "Le Gérant") -> tuple[str, str]:
    """Returns (text, mode)."""
    base = _template(a, signataire)
    if not llm.available():
        return base, "hors_ligne"
    prompt = ("Améliore la rédaction de ce brouillon de lettre d'opposition à une notification de redressement fiscal "
              "tunisienne : style administratif clair, arguments mieux enchaînés. Garde exactement les mêmes faits, "
              "montants, dates, références et articles ; n'en ajoute aucun. Garde la mention finale de relecture.\n\n" + base)
    try:
        return llm.parse("draft", prompt, _Draft).lettre, "ia"
    except llm.LLMUnavailable:
        return base, "hors_ligne"
