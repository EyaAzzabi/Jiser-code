"""Business reference data: reassessment types and CDPF procedure rules.

Procedure rules are taken from the Code des droits et procédures fiscaux (CDPF),
text scraped from Jurisite Tunisie (data/legal/cdpf.json). Article numbers are
cited so every alert can be traced back to the law.
"""
from __future__ import annotations

# --- Types of reassessment items ("chefs de redressement") -----------------------------------
# weight_* values drive the synthetic outcome model: how often this kind of item is upheld
# when the procedure is clean and the file is well documented.
CHEF_TYPES: dict[str, dict] = {
    "TVA_FACTURES_NON_CONFORMES": {
        "label": "TVA déduite sur des factures non conformes ou fictives",
        "impot": "TVA",
        "articles": ["ctva-art-9", "ctva-art-18"],
        "pieces": ["Factures d'achat originales", "Preuves de paiement (virements, chèques)",
                   "Bons de livraison", "Identifiant fiscal du fournisseur"],
        "base_uphold": 0.70,
    },
    "CHARGES_NON_DEDUCTIBLES": {
        "label": "Charges non déductibles réintégrées au résultat",
        "impot": "IS",
        "articles": ["cirppis-art-11", "cirppis-art-12"],
        "pieces": ["Factures et contrats justifiant les charges", "Lien des charges avec l'activité",
                   "Grand livre des comptes de charges"],
        "base_uphold": 0.55,
    },
    "MINORATION_CA": {
        "label": "Minoration du chiffre d'affaires (recettes non déclarées)",
        "impot": "IS",
        "articles": ["cdpf-art-38"],
        "pieces": ["Relevés bancaires", "Journal des ventes", "Inventaires de stock",
                   "Rapprochement CA déclaré / encaissements"],
        "base_uphold": 0.60,
    },
    "RECONSTITUTION_CA": {
        "label": "Reconstitution du chiffre d'affaires par présomptions",
        "impot": "IS",
        "articles": ["cdpf-art-38"],
        "pieces": ["Comptabilité complète et régulière", "Justificatifs des marges pratiquées",
                   "Pièces sur les pertes et invendus"],
        "base_uphold": 0.45,
    },
    "RETENUE_SOURCE_NON_EFFECTUEE": {
        "label": "Retenue à la source non effectuée ou non reversée",
        "impot": "RS",
        "articles": ["cirppis-art-52"],
        "pieces": ["Déclarations mensuelles de retenue", "Certificats de retenue remis",
                   "Preuves de reversement"],
        "base_uphold": 0.75,
    },
    "AVANTAGES_ENTREPRISES_LIEES": {
        "label": "Avantages accordés à des entreprises liées (prix de transfert)",
        "impot": "IS",
        "articles": ["cirppis-art-48"],
        "pieces": ["Documentation prix de transfert", "Contrats intra-groupe",
                   "Comparables de prix de marché"],
        "base_uphold": 0.50,
    },
}

# --- CDPF procedure rules -------------------------------------------------------------------
# CDPF, édition officielle 2024 : 45 jours depuis la loi de finances 2015 (l'ancienne version disait 30)
DELAI_REPONSE_JOURS = 45          # art. 43 et 44 : vérification préliminaire ou approfondie
DELAI_REPONSE_PONCTUELLE_JOURS = 10   # art. 43 : vérification ponctuelle
DELAI_REPONSE_ADMIN_JOURS = 90    # art. 44 bis : l'administration répond à l'opposition sous 90 jours
DELAI_REPLIQUE_JOURS = 15         # art. 44 bis : 15 jours pour répliquer à la réponse de l'administration
DELAI_AVIS_MIN_JOURS = 15         # art. 39 : début de vérification >= 15 jours après l'avis
DUREE_MAX_COMPTA_MOIS = 6         # art. 40 : 6 mois si comptabilité conforme
DUREE_MAX_AUTRES_MOIS = 12        # art. 40 : 1 an dans les autres cas
DROIT_REPRISE_ANS = 4             # art. 19 : 4 ans
DROIT_REPRISE_NON_DECLARE_ANS = 10  # art. 20 : 10 ans pour les impôts non déclarés
SUSPENSION_TAUX = 0.20            # art. 52 : suspension de l'exécution contre paiement de 20 %

PROCEDURE_RULES: list[dict] = [
    {"code": "AVIS_PREALABLE", "article": "cdpf-art-39",
     "label": "Avis préalable de vérification approfondie notifié"},
    {"code": "DELAI_AVIS_15J", "article": "cdpf-art-39",
     "label": "Début de la vérification au moins 15 jours après l'avis"},
    {"code": "MENTION_ASSISTANCE", "article": "cdpf-art-39",
     "label": "Mention du droit de se faire assister dans l'avis"},
    {"code": "DUREE_MAX", "article": "cdpf-art-40",
     "label": "Durée de la vérification approfondie respectée (6 mois / 1 an)"},
    {"code": "CHEFS_MOTIVES", "article": "cdpf-art-43",
     "label": "Chefs de redressement et méthode de calcul indiqués"},
    {"code": "MENTION_DELAI_30J", "article": "cdpf-art-43",
     "label": "Invitation à répondre dans le délai légal de 45 jours"},
    {"code": "PENALITES_INDIQUEES", "article": "cdpf-art-43",
     "label": "Montant de l'impôt et des pénalités indiqués"},
    {"code": "DROIT_REPRISE", "article": "cdpf-art-19",
     "label": "Exercices vérifiés dans le délai de reprise (4 ans)"},
]

GOUVERNORATS = [
    "Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Zaghouan", "Bizerte", "Béja",
    "Jendouba", "Le Kef", "Siliana", "Sousse", "Monastir", "Mahdia", "Sfax", "Kairouan",
    "Kasserine", "Sidi Bouzid", "Gabès", "Médenine", "Tataouine", "Gafsa", "Tozeur", "Kébili",
]
# rough economic weight, used only to spread synthetic companies realistically
GOUV_WEIGHTS = [18, 7, 7, 3, 7, 1, 4, 2, 1, 1, 1, 8, 5, 2, 12, 3, 1, 2, 3, 3, 1, 2, 1, 1]

SECTEURS = ["Commerce de gros", "Commerce de détail", "BTP", "Industrie textile",
            "Agroalimentaire", "Services informatiques", "Transport et logistique",
            "Promotion immobilière", "Tourisme et hôtellerie", "Professions libérales"]

ETAPES = ["Notification", "Réponse du contribuable", "Réplique de l'administration",
          "Taxation d'office", "Tribunal de première instance", "Cour d'appel"]
