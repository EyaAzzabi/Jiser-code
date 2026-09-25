"""Generate synthetic tax-dispute files (dossiers) for JISER.

Everything here is fictitious: company names, tax IDs and amounts are random. Outcomes are
produced by explicit business rules plus noise (see `simulate_outcome`), so the ML model
learns a known, documented structure. With real data, the model would be retrained on the
administration's own history.

Outputs (data/synthetic/):
    dossiers.json      closed (historical) and open files
    eval_set.json      30 notifications with their letter text, for extraction evaluation
    samples/*.pdf      demo notifications to upload in the app

Usage:
    python scripts/generate_synthetic.py
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain import (CHEF_TYPES, DROIT_REPRISE_ANS, DUREE_MAX_AUTRES_MOIS,  # noqa: E402
                        DUREE_MAX_COMPTA_MOIS, ETAPES, GOUV_WEIGHTS, GOUVERNORATS, SECTEURS)
from app.schemas import ChefIssue, ChefRedressement, Dossier, Entreprise, Notification  # noqa: E402
from app.services.letter import render  # noqa: E402

SEED = 2026
N_CLOSED = 2500
N_OPEN = 320
TODAY = date(2026, 9, 25)
OUT = ROOT / "data" / "synthetic"

NAME_PARTS = ["El Amen", "Carthage", "Méditerranée", "Nour", "Sahel", "Atlas", "Jasmin", "Hannibal",
              "Zitouna", "Oasis", "Kerkennah", "Didon", "El Baraka", "Salama", "Byrsa", "Djerba",
              "Ennasr", "Tabarka", "El Manar", "Kairouan", "Ulysse", "Cap Bon", "Horizon", "Essalem"]
ACTIVITY_WORDS = {
    "Commerce de gros": ["Distribution", "Négoce", "Import-Export"],
    "Commerce de détail": ["Commerce", "Boutiques", "Market"],
    "BTP": ["Construction", "Travaux", "Bâtiment"],
    "Industrie textile": ["Textile", "Confection", "Tissage"],
    "Agroalimentaire": ["Agro", "Huilerie", "Conserverie"],
    "Services informatiques": ["Digital", "Informatique", "Soft"],
    "Transport et logistique": ["Transport", "Logistique", "Trans"],
    "Promotion immobilière": ["Immobilière", "Promotion", "Résidences"],
    "Tourisme et hôtellerie": ["Hôtels", "Voyages", "Tourisme"],
    "Professions libérales": ["Cabinet", "Bureau d'études", "Clinique"],
}
FORMES = ["SARL", "SA", "SUARL"]

MOTIVATIONS = {
    "TVA_FACTURES_NON_CONFORMES": {
        "detaillee": "Les factures n° {a} à {b} émises par le fournisseur {f} ne comportent pas l'identifiant fiscal "
                     "du fournisseur et ne sont appuyées d'aucune preuve de paiement ni de livraison. Le fournisseur "
                     "n'a déposé aucune déclaration sur la période. La TVA correspondante est réintégrée.",
        "sommaire": "Factures non conformes, TVA non déductible.",
    },
    "CHARGES_NON_DEDUCTIBLES": {
        "detaillee": "Les charges comptabilisées au compte 62 (honoraires et commissions) pour un total de {m} DT ne "
                     "sont pas justifiées par des pièces probantes et ne présentent pas de lien établi avec l'activité "
                     "de l'entreprise. Elles sont réintégrées au résultat fiscal.",
        "sommaire": "Charges non justifiées réintégrées.",
    },
    "MINORATION_CA": {
        "detaillee": "Le rapprochement entre les encaissements figurant sur les relevés bancaires et le chiffre "
                     "d'affaires déclaré fait apparaître un écart de {m} DT non justifié, considéré comme des recettes "
                     "non déclarées.",
        "sommaire": "Écart entre encaissements et chiffre d'affaires déclaré.",
    },
    "RECONSTITUTION_CA": {
        "detaillee": "La comptabilité n'ayant pas été admise, le chiffre d'affaires a été reconstitué à partir des achats "
                     "revendus affectés d'un coefficient de marge de {c} observé sur un échantillon de factures de vente.",
        "sommaire": "Chiffre d'affaires reconstitué par application d'un coefficient de marge.",
    },
    "RETENUE_SOURCE_NON_EFFECTUEE": {
        "detaillee": "Les honoraires versés à des prestataires résidents pour {m} DT n'ont pas fait l'objet de la retenue "
                     "à la source prévue par l'article 52 du code de l'IRPP et de l'IS.",
        "sommaire": "Retenue à la source non effectuée.",
    },
    "AVANTAGES_ENTREPRISES_LIEES": {
        "detaillee": "Les ventes à la société liée {f} ont été facturées à des prix inférieurs de {p} % aux prix pratiqués "
                     "avec des clients indépendants pour des produits comparables. L'avantage consenti est réintégré.",
        "sommaire": "Prix de vente anormalement bas avec une société liée.",
    },
}
METHODES = {
    "TVA_FACTURES_NON_CONFORMES": "Réintégration de la TVA déduite sur les factures concernées",
    "CHARGES_NON_DEDUCTIBLES": "Réintégration des charges au résultat imposable",
    "MINORATION_CA": "Rapprochement bancaire (encaissements / chiffre d'affaires déclaré)",
    "RECONSTITUTION_CA": "Reconstitution par coefficient de marge",
    "RETENUE_SOURCE_NON_EFFECTUEE": "Application du taux de retenue aux montants versés",
    "AVANTAGES_ENTREPRISES_LIEES": "Comparaison avec les prix de marché (méthode du prix comparable)",
}
ARTICLE_TXT = {
    "ctva-art-9": "article 9 du Code de la TVA",
    "ctva-art-18": "article 18 du Code de la TVA",
    "cirppis-art-11": "article 11 du Code de l'IRPP et de l'IS",
    "cirppis-art-12": "article 12 du Code de l'IRPP et de l'IS",
    "cirppis-art-48": "article 48 du Code de l'IRPP et de l'IS",
    "cirppis-art-52": "article 52 du Code de l'IRPP et de l'IS",
    "cdpf-art-38": "article 38 du CDPF",
}


def rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def matricule(rng: random.Random) -> str:
    # Synthetic identifier shaped like a Tunisian tax ID (7 digits + key letter / category codes)
    return f"{rng.randint(1000000, 1999999)}{rng.choice('ABCDEFGHJKLMNPQRSTVWXYZ')}/{rng.choice('AMP')}/M/000"


def make_entreprise(rng: random.Random) -> Entreprise:
    secteur = rng.choice(SECTEURS)
    taille = rng.choices(["TPE", "PME", "GE"], weights=[35, 50, 15])[0]
    nom = f"Société {rng.choice(ACTIVITY_WORDS[secteur])} {rng.choice(NAME_PARTS)} {rng.choice(FORMES)}"
    return Entreprise(nom=nom, matricule_fiscal=matricule(rng), secteur=secteur, taille=taille,
                      gouvernorat=rng.choices(GOUVERNORATS, weights=GOUV_WEIGHTS)[0])


def make_chef(rng: random.Random, idx: int, ctype: str, exercice: int, taille: str,
              motivation_qualite: str) -> ChefRedressement:
    meta = CHEF_TYPES[ctype]
    scale = {"TPE": 15_000, "PME": 60_000, "GE": 400_000}[taille]
    principal = round(rng.lognormvariate(0, 0.7) * scale / 1000) * 1000.0
    principal = max(principal, 1000.0)
    penalites = round(principal * rng.uniform(0.10, 0.35), 3)
    if motivation_qualite == "absente":
        motivation = ""
    else:
        motivation = MOTIVATIONS[ctype][motivation_qualite].format(
            a=rng.randint(100, 400), b=rng.randint(401, 900), f=f"Société {rng.choice(NAME_PARTS)} SARL",
            m=f"{principal * rng.uniform(3, 6):,.0f}".replace(",", " "), c=round(rng.uniform(1.2, 1.8), 2),
            p=rng.randint(15, 40))
    article = rng.choice(meta["articles"])
    return ChefRedressement(
        id=f"C{idx}", type=ctype, libelle=meta["label"], impot=meta["impot"], exercice=exercice,
        montant_principal=principal, penalites=penalites,
        article_invoque=ARTICLE_TXT.get(article, article) if motivation_qualite != "absente" or rng.random() < 0.5 else None,
        motivation=motivation, motivation_qualite=motivation_qualite, methode=METHODES[ctype])


def make_notification(rng: random.Random, ref: str, notif_date: date, inject_defects: bool = True) -> Notification:
    ent = make_entreprise(rng)
    approfondie = rng.random() < 0.8
    compta = rng.random() < 0.7
    defect = inject_defects and rng.random() < 0.28   # ~28 % of files carry at least one procedure defect
    kinds = rng.sample(["delai_avis", "assistance", "duree", "delai_30j", "penalites", "reprise"],
                       k=rng.choice([1, 1, 1, 2])) if defect else []

    max_months = DUREE_MAX_COMPTA_MOIS if compta else DUREE_MAX_AUTRES_MOIS
    if approfondie:
        months = rng.uniform(max_months + 0.4, max_months + 3) if "duree" in kinds else rng.uniform(1.5, max_months - 0.3)
        debut = notif_date - timedelta(days=int(months * 30.4))
        gap = rng.randint(3, 12) if "delai_avis" in kinds else rng.randint(15, 30)
        avis = debut - timedelta(days=gap)
    else:
        debut = avis = None

    last_year = notif_date.year - 1
    if "reprise" in kinds:
        exercices = [notif_date.year - DROIT_REPRISE_ANS - 1, notif_date.year - DROIT_REPRISE_ANS]
    else:
        n_years = rng.choice([1, 2, 2, 3])
        exercices = sorted({last_year - i for i in range(n_years)})

    n_chefs = rng.choices([1, 2, 3, 4], weights=[25, 35, 28, 12])[0]
    types = rng.sample(list(CHEF_TYPES), k=n_chefs)
    if not compta and "RECONSTITUTION_CA" not in types and rng.random() < 0.5:
        types[0] = "RECONSTITUTION_CA"
    chefs = []
    for i, t in enumerate(types, 1):
        q = rng.choices(["detaillee", "sommaire", "absente"], weights=[62, 28, 10])[0]
        chefs.append(make_chef(rng, i, t, rng.choice(exercices), ent.taille, q))

    centre = ("Direction des grandes entreprises" if ent.taille == "GE"
              else f"Centre régional de contrôle des impôts de {ent.gouvernorat}")
    return Notification(
        reference=ref, centre=centre, type_verification="approfondie" if approfondie else "preliminaire",
        comptabilite_conforme=compta, date_avis=avis, date_debut_verification=debut, date_notification=notif_date,
        exercices_verifies=exercices, mention_assistance="assistance" not in kinds,
        mention_delai_30j="delai_30j" not in kinds, penalites_indiquees="penalites" not in kinds,
        entreprise=ent, chefs=chefs)


def procedure_defects(n: Notification) -> list[str]:
    """Ground-truth defects, mirroring services/procedure.py (kept independent on purpose)."""
    d = []
    if n.type_verification == "approfondie":
        if n.date_avis and n.date_debut_verification and (n.date_debut_verification - n.date_avis).days < 15:
            d.append("DELAI_AVIS_15J")
        if not n.mention_assistance:
            d.append("MENTION_ASSISTANCE")
        max_m = DUREE_MAX_COMPTA_MOIS if n.comptabilite_conforme else DUREE_MAX_AUTRES_MOIS
        if n.date_debut_verification and (n.date_notification - n.date_debut_verification).days > max_m * 30.4:
            d.append("DUREE_MAX")
    if not n.mention_delai_30j:
        d.append("MENTION_DELAI_30J")
    if not n.penalites_indiquees:
        d.append("PENALITES_INDIQUEES")
    if any(n.date_notification.year > y + DROIT_REPRISE_ANS for y in n.exercices_verifies):
        d.append("DROIT_REPRISE")
    return d


def simulate_outcome(rng: random.Random, n: Notification, pieces: float, reponse: bool) -> list[ChefIssue]:
    """Documented synthetic rules: procedure defects and weak motivation get reassessments cancelled,
    strong supporting documents get them reduced."""
    vices = procedure_defects(n)
    issues = []
    for c in n.chefs:
        total = c.montant_principal + c.penalites
        if n.date_notification.year > c.exercice + DROIT_REPRISE_ANS:
            issues.append(ChefIssue(chef_id=c.id, issue="annule", montant_final=0.0))
            continue
        p = CHEF_TYPES[c.type]["base_uphold"]
        if vices:
            p *= 0.2
        p *= {"detaillee": 1.0, "sommaire": 0.8, "absente": 0.35}[c.motivation_qualite]
        if not c.article_invoque:
            p *= 0.85
        p *= 1 - 0.55 * pieces
        if not reponse:
            p = min(0.97, p * 1.2)
        p = min(0.97, max(0.02, p + rng.gauss(0, 0.07)))
        u = rng.random()
        if u < p:
            issues.append(ChefIssue(chef_id=c.id, issue="maintenu", montant_final=round(total, 3)))
        elif u < p + (1 - p) * 0.5:
            issues.append(ChefIssue(chef_id=c.id, issue="reduit", montant_final=round(total * rng.uniform(0.3, 0.7), 3)))
        else:
            issues.append(ChefIssue(chef_id=c.id, issue="annule", montant_final=0.0))
    return issues


def sami_notification() -> Notification:
    """The demo file used in the pitch: a Sfax distributor with a verification that lasted too long."""
    ent = Entreprise(nom="Société Distribution El Amen SARL", matricule_fiscal="1478523K/A/M/000",
                     secteur="Commerce de gros", taille="PME", gouvernorat="Sfax")
    chefs = [
        ChefRedressement(id="C1", type="TVA_FACTURES_NON_CONFORMES", libelle=CHEF_TYPES["TVA_FACTURES_NON_CONFORMES"]["label"],
                         impot="TVA", exercice=2024, montant_principal=42000.0, penalites=8400.0,
                         article_invoque="article 9 du Code de la TVA", methode=METHODES["TVA_FACTURES_NON_CONFORMES"],
                         motivation="Les factures n° 214 à 262 émises par le fournisseur Société Byrsa Négoce SARL ne comportent "
                                    "pas l'identifiant fiscal du fournisseur et ne sont appuyées d'aucune preuve de paiement ni de "
                                    "livraison. La TVA correspondante est réintégrée.",
                         motivation_qualite="detaillee"),
        ChefRedressement(id="C2", type="MINORATION_CA", libelle=CHEF_TYPES["MINORATION_CA"]["label"],
                         impot="IS", exercice=2024, montant_principal=96000.0, penalites=19200.0,
                         article_invoque="article 38 du CDPF", methode=METHODES["MINORATION_CA"],
                         motivation="Écart entre encaissements et chiffre d'affaires déclaré.",
                         motivation_qualite="sommaire"),
        ChefRedressement(id="C3", type="CHARGES_NON_DEDUCTIBLES", libelle=CHEF_TYPES["CHARGES_NON_DEDUCTIBLES"]["label"],
                         impot="IS", exercice=2023, montant_principal=12000.0, penalites=2400.0,
                         article_invoque=None, methode=METHODES["CHARGES_NON_DEDUCTIBLES"], motivation="",
                         motivation_qualite="absente"),
    ]
    return Notification(
        reference="NR-2026-SF-004127", centre="Centre régional de contrôle des impôts de Sfax",
        type_verification="approfondie", comptabilite_conforme=True,
        date_avis=date(2025, 12, 1), date_debut_verification=date(2025, 12, 22),
        date_notification=date(2026, 9, 10),   # 8.6 months > 6 months (art. 40) -> procedure defect
        exercices_verifies=[2023, 2024], mention_assistance=True, mention_delai_30j=True,
        penalites_indiquees=True, entreprise=ent, chefs=chefs)


def clean_notification() -> Notification:
    """A second demo file with a clean procedure, to contrast with Sami's."""
    ent = Entreprise(nom="Société Textile Jasmin SA", matricule_fiscal="1325874M/A/M/000",
                     secteur="Industrie textile", taille="PME", gouvernorat="Monastir")
    chefs = [
        ChefRedressement(id="C1", type="RETENUE_SOURCE_NON_EFFECTUEE", libelle=CHEF_TYPES["RETENUE_SOURCE_NON_EFFECTUEE"]["label"],
                         impot="RS", exercice=2025, montant_principal=18000.0, penalites=3600.0,
                         article_invoque="article 52 du Code de l'IRPP et de l'IS", methode=METHODES["RETENUE_SOURCE_NON_EFFECTUEE"],
                         motivation=MOTIVATIONS["RETENUE_SOURCE_NON_EFFECTUEE"]["detaillee"].format(m="120 000"),
                         motivation_qualite="detaillee"),
    ]
    return Notification(
        reference="NR-2026-MO-001893", centre="Centre régional de contrôle des impôts de Monastir",
        type_verification="approfondie", comptabilite_conforme=True,
        date_avis=date(2026, 3, 2), date_debut_verification=date(2026, 3, 23), date_notification=date(2026, 9, 8),
        exercices_verifies=[2025], mention_assistance=True, mention_delai_30j=True, penalites_indiquees=True,
        entreprise=ent, chefs=chefs)


def write_pdf(text: str, path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)
    story = []
    for line in text.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 8))
            continue
        style = styles["Heading3"] if line.startswith(("NOTIFICATION", "CHEF N°", "RÉCAPITULATIF")) else styles["Normal"]
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), style))
    doc.build(story)


def main() -> None:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "samples").mkdir(exist_ok=True)
    dossiers: list[Dossier] = []

    for i in range(N_CLOSED):
        nd = rand_date(rng, date(2020, 1, 1), date(2025, 6, 30))
        n = make_notification(rng, f"NR-{nd.year}-{i:05d}", nd)
        pieces = round(rng.betavariate(2, 2.5), 2)
        reponse = rng.random() < 0.82
        issues = simulate_outcome(rng, n, pieces, reponse)
        etape = rng.choices(["Conciliation (accord)", "Tribunal de première instance", "Cour d'appel"], weights=[45, 40, 15])[0]
        dossiers.append(Dossier(
            id=f"D-{i:05d}", notification=n, etape=etape,
            date_etape=nd + timedelta(days=rng.randint(120, 1300)), pieces_fournies_ratio=pieces,
            reponse_contribuable=reponse, statut="cloture", issues=issues,
            montant_recouvre=round(sum(x.montant_final for x in issues), 3)))

    for j in range(N_OPEN):
        nd = rand_date(rng, date(2023, 1, 1), TODAY - timedelta(days=5))
        n = make_notification(rng, f"NR-{nd.year}-{N_CLOSED + j:05d}", nd)
        age = (TODAY - nd).days
        etape = (ETAPES[0] if age < 30 else rng.choices(ETAPES[1:], weights=[30, 20, 25, 15, 10])[0])
        dossiers.append(Dossier(
            id=f"D-{N_CLOSED + j:05d}", notification=n, etape=etape,
            date_etape=min(TODAY, nd + timedelta(days=rng.randint(0, max(1, age)))),
            pieces_fournies_ratio=round(rng.betavariate(2, 2.5), 2), reponse_contribuable=etape != ETAPES[0],
            statut="en_cours"))

    for demo_id, n, pieces in (("D-SAMI", sami_notification(), 0.55), ("D-JASMIN", clean_notification(), 0.2)):
        dossiers.append(Dossier(id=demo_id, notification=n, etape=ETAPES[0], date_etape=n.date_notification,
                                pieces_fournies_ratio=pieces, reponse_contribuable=False, statut="en_cours"))
        pdf = OUT / "samples" / f"notification_{demo_id[2:].lower()}.pdf"
        write_pdf(render(n), pdf)
        (pdf.with_suffix(".txt")).write_text(render(n), encoding="utf-8")

    (OUT / "dossiers.json").write_text(
        json.dumps([d.model_dump(mode="json") for d in dossiers], ensure_ascii=False), encoding="utf-8")

    # Evaluation set for extraction: letter text + ground truth (defects included)
    eval_rng = random.Random(SEED + 1)
    eval_items = []
    for k in range(30):
        n = make_notification(eval_rng, f"NR-EVAL-{k:03d}", rand_date(eval_rng, date(2025, 1, 1), date(2026, 9, 1)))
        eval_items.append({"text": render(n), "truth": n.model_dump(mode="json"), "defects": procedure_defects(n)})
    (OUT / "eval_set.json").write_text(json.dumps(eval_items, ensure_ascii=False, indent=1), encoding="utf-8")

    closed = [d for d in dossiers if d.statut == "cloture"]
    with_defect = sum(1 for d in closed if procedure_defects(d.notification))
    rate = sum(d.montant_recouvre or 0 for d in closed) / sum(d.notification.montant_total for d in closed)
    print(f"{len(closed)} closed + {len(dossiers) - len(closed)} open dossiers written")
    print(f"closed files with a procedure defect: {with_defect / len(closed):.0%}; amount recovered: {rate:.0%}")
    print(f"samples: {[p.name for p in (OUT / 'samples').glob('*.pdf')]}")


if __name__ == "__main__":
    main()
