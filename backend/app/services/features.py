"""Feature engineering for the per-item (chef de redressement) outcome model.

Shared by scripts/train_model.py and the API so training and serving use identical features.
"""
from __future__ import annotations

import math

from ..domain import CHEF_TYPES, DROIT_REPRISE_ANS
from ..schemas import ChefRedressement, Dossier
from .procedure import vice_codes

VICE_FEATURES = ["DELAI_AVIS_15J", "MENTION_ASSISTANCE", "DUREE_MAX", "MENTION_DELAI_30J",
                 "PENALITES_INDIQUEES", "DROIT_REPRISE"]

# Human-readable label for each feature, used to explain scores (SHAP) in the UI
FEATURE_LABELS: dict[str, str] = {
    **{f"type_{k}": f"Type : {v['label']}" for k, v in CHEF_TYPES.items()},
    "log_montant": "Montant du redressement",
    "motivation_absente": "Motivation absente",
    "motivation_sommaire": "Motivation sommaire",
    "sans_article": "Base légale non citée",
    "exercice_hors_delai": "Exercice hors délai de reprise",
    "anciennete_exercice": "Ancienneté de l'exercice",
    "vice_DELAI_AVIS_15J": "Vice : vérification commencée moins de 15 jours après l'avis",
    "vice_MENTION_ASSISTANCE": "Vice : droit à l'assistance non mentionné",
    "vice_DUREE_MAX": "Vice : durée maximale de vérification dépassée",
    "vice_MENTION_DELAI_30J": "Vice : délai de réponse de 30 jours non indiqué",
    "vice_PENALITES_INDIQUEES": "Vice : pénalités non chiffrées",
    "vice_DROIT_REPRISE": "Vice : exercice hors délai de reprise",
    "nb_vices": "Nombre de vices de procédure",
    "approfondie": "Vérification approfondie",
    "compta_conforme": "Comptabilité conforme",
    "pieces_ratio": "Justificatifs produits par le contribuable",
    "reponse": "Réponse du contribuable dans les délais",
    "taille_TPE": "Entreprise TPE",
    "taille_GE": "Grande entreprise",
    "nb_chefs": "Nombre de chefs de redressement",
}
FEATURE_NAMES = list(FEATURE_LABELS)


def chef_features(d: Dossier, c: ChefRedressement, vices: set[str] | None = None) -> dict[str, float]:
    n = d.notification
    vices = vice_codes(n) if vices is None else vices
    f: dict[str, float] = {f"type_{k}": float(c.type == k) for k in CHEF_TYPES}
    f.update({
        "log_montant": math.log1p(c.montant_principal + c.penalites),
        "motivation_absente": float(c.motivation_qualite == "absente"),
        "motivation_sommaire": float(c.motivation_qualite == "sommaire"),
        "sans_article": float(not c.article_invoque),
        "exercice_hors_delai": float(n.date_notification.year > c.exercice + DROIT_REPRISE_ANS),
        "anciennete_exercice": float(n.date_notification.year - c.exercice),
        **{f"vice_{v}": float(v in vices) for v in VICE_FEATURES},
        "nb_vices": float(len(vices)),
        "approfondie": float(n.type_verification == "approfondie"),
        "compta_conforme": float(n.comptabilite_conforme),
        "pieces_ratio": d.pieces_fournies_ratio,
        "reponse": float(d.reponse_contribuable),
        "taille_TPE": float(n.entreprise.taille == "TPE"),
        "taille_GE": float(n.entreprise.taille == "GE"),
        "nb_chefs": float(len(n.chefs)),
    })
    return f


def dossier_rows(d: Dossier) -> list[list[float]]:
    vices = vice_codes(d.notification)
    return [[chef_features(d, c, vices)[k] for k in FEATURE_NAMES] for c in d.notification.chefs]
