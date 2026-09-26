"""Render a Notification as a French administrative letter, and parse that format back.

The renderer produces the synthetic notifications (PDF samples, evaluation set).
The parser is the offline fallback for extraction: it only understands letters in this
format. Real, free-form notifications go through the LLM extractor (services/extraction.py).
"""
from __future__ import annotations

import re
from datetime import date, datetime

from ..domain import CHEF_TYPES
from ..schemas import ChefRedressement, Entreprise, Notification


def fmt_dt(amount: float) -> str:
    """12345.5 -> '12 345,500 DT' (Tunisian dinar, 3 decimals)."""
    whole, dec = f"{amount:,.3f}".split(".")
    return f"{whole.replace(',', ' ')},{dec} DT"


def parse_dt(text: str) -> float:
    return float(text.replace("DT", "").replace(" ", "").replace(" ", "").replace(",", ".").strip())


def fmt_date(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def parse_date(text: str) -> date | None:
    text = text.strip()
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None


def render(n: Notification) -> str:
    lines = [
        "RÉPUBLIQUE TUNISIENNE",
        "MINISTÈRE DES FINANCES",
        "Direction Générale des Impôts",
        n.centre,
        "",
        "NOTIFICATION DES RÉSULTATS DE LA VÉRIFICATION FISCALE",
        f"Référence : {n.reference}",
        f"Date de notification : {fmt_date(n.date_notification)}",
        "",
        f"Destinataire : {n.entreprise.nom}",
        f"Matricule fiscal : {n.entreprise.matricule_fiscal}",
        f"Activité : {n.entreprise.secteur}",
        f"Gouvernorat : {n.entreprise.gouvernorat}",
        f"Taille : {n.entreprise.taille}",
        "",
        f"Nature de la vérification : vérification {'approfondie' if n.type_verification == 'approfondie' else 'préliminaire'}",
    ]
    if n.type_verification == "approfondie":
        lines.append(f"Avis de vérification notifié le : {fmt_date(n.date_avis)}")
        lines.append(f"Date de début de la vérification : {fmt_date(n.date_debut_verification)}")
        lines.append("Comptabilité : " + ("jugée conforme à la législation fiscale" if n.comptabilite_conforme
                                          else "non admise (non probante)"))
    lines.append("Exercices vérifiés : " + ", ".join(str(y) for y in n.exercices_verifies))
    lines += [
        "",
        "Madame, Monsieur,",
        "À l'issue de la vérification de votre situation fiscale, nous avons l'honneur de vous notifier, "
        "conformément à l'article 43 du Code des droits et procédures fiscaux, les redressements suivants.",
    ]
    if n.mention_assistance:
        lines.append("Vous pouvez vous faire assister, pour la discussion de ces résultats, par une personne "
                     "de votre choix ou vous faire représenter par un mandataire (article 42 du CDPF).")
    for i, c in enumerate(n.chefs, 1):
        lines += [
            "",
            f"CHEF N°{i} : {c.libelle}",
            f"Impôt : {c.impot} — Exercice : {c.exercice}",
            f"Base légale : {c.article_invoque or 'non précisée'}",
            f"Méthode : {c.methode or 'non précisée'}",
            f"Motivation : {c.motivation or 'Néant.'}",
            f"Montant en principal : {fmt_dt(c.montant_principal)}",
            "Pénalités : " + (fmt_dt(c.penalites) if n.penalites_indiquees else "selon la législation en vigueur"),
        ]
    total_p = sum(c.montant_principal for c in n.chefs)
    total_pen = sum(c.penalites for c in n.chefs)
    lines += ["", "RÉCAPITULATIF", f"Total en principal : {fmt_dt(total_p)}"]
    if n.penalites_indiquees:
        lines += [f"Total des pénalités : {fmt_dt(total_pen)}", f"TOTAL EXIGIBLE : {fmt_dt(total_p + total_pen)}"]
    lines.append("")
    if n.mention_delai_30j:
        lines.append("Vous êtes invité(e) à formuler par écrit vos observations, oppositions et réserves dans un "
                     "délai de quarante-cinq (45) jours à compter de la date de la présente notification "
                     "(articles 43 et 44 du CDPF). À défaut, la taxation sera établie d'office (article 47).")
    else:
        lines.append("Nous vous prions de nous faire part de vos observations.")
    lines += ["", "Le Chef de centre", "(document synthétique généré pour le prototype JISER)"]
    return "\n".join(lines)


# ---- Parser (offline fallback) -------------------------------------------------------------

def _field(text: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}\s*:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _type_from_label(libelle: str) -> str:
    for key, meta in CHEF_TYPES.items():
        if meta["label"].lower() == libelle.lower():
            return key
    return "AUTRE"


def parse(text: str) -> Notification | None:
    """Parse a letter produced by render(). Returns None if the text is not in that format."""
    ref = _field(text, "Référence")
    notif_date = parse_date(_field(text, "Date de notification") or "")
    if not ref or not notif_date:
        return None
    nature = (_field(text, "Nature de la vérification") or "").lower()
    compta = (_field(text, "Comptabilité") or "").lower()
    penalites_indiquees = "selon la législation" not in text
    chefs: list[ChefRedressement] = []
    blocks = re.split(r"^CHEF N°(\d+) : ", text, flags=re.MULTILINE)
    for i in range(1, len(blocks) - 1, 2):
        num, block = blocks[i], blocks[i + 1]
        libelle = block.splitlines()[0].strip()
        impot_m = re.search(r"^Impôt : (\S+) — Exercice : (\d{4})", block, re.MULTILINE)
        motivation = _field(block, "Motivation") or ""
        pen = _field(block, "Pénalités") or "0"
        chefs.append(ChefRedressement(
            id=f"C{num}",
            type=_type_from_label(libelle),
            libelle=libelle,
            impot=impot_m.group(1) if impot_m else "?",
            exercice=int(impot_m.group(2)) if impot_m else notif_date.year - 1,
            montant_principal=parse_dt(_field(block, "Montant en principal") or "0"),
            penalites=0.0 if "selon" in pen else parse_dt(pen),
            article_invoque=base if (base := _field(block, "Base légale")) and base != "non précisée" else None,
            motivation="" if motivation == "Néant." else motivation,
            motivation_qualite="absente" if motivation in ("", "Néant.") else
            ("sommaire" if len(motivation) < 90 else "detaillee"),
            methode=_field(block, "Méthode") or "",
        ))
    exercices = [int(y) for y in re.findall(r"\d{4}", _field(text, "Exercices vérifiés") or "")]
    return Notification(
        reference=ref,
        centre=text.splitlines()[3].strip() if len(text.splitlines()) > 3 else "",
        type_verification="approfondie" if "approfondie" in nature else "preliminaire",
        comptabilite_conforme="non admise" not in compta,
        date_avis=parse_date(_field(text, "Avis de vérification notifié le") or ""),
        date_debut_verification=parse_date(_field(text, "Date de début de la vérification") or ""),
        date_notification=notif_date,
        exercices_verifies=exercices,
        mention_assistance="faire assister" in text,
        mention_delai_30j=("quarante-cinq (45) jours" in text or "trente (30) jours" in text),
        penalites_indiquees=penalites_indiquees,
        entreprise=Entreprise(
            nom=_field(text, "Destinataire") or "",
            matricule_fiscal=_field(text, "Matricule fiscal") or "",
            secteur=_field(text, "Activité") or "",
            taille=(_field(text, "Taille") or "PME") if (_field(text, "Taille") or "PME") in ("TPE", "PME", "GE") else "PME",
            gouvernorat=_field(text, "Gouvernorat") or "",
        ),
        chefs=chefs,
    )
