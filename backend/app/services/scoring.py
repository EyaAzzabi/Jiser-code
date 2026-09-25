"""Serve the per-item outcome model: probabilities, file solidity score and SHAP explanations."""
from __future__ import annotations

from functools import lru_cache

import joblib
import numpy as np
import shap

from ..config import MODELS_DIR
from ..schemas import Dossier, ScoreDossier, ScoreExplication
from .features import FEATURE_LABELS, FEATURE_NAMES, dossier_rows

RECOVERY_WEIGHT = np.array([1.0, 0.5, 0.0])   # maintenu, réduit, annulé


@lru_cache(maxsize=1)
def _bundle() -> dict:
    bundle = joblib.load(MODELS_DIR / "chef_model.joblib")
    if bundle["features"] != FEATURE_NAMES:
        raise RuntimeError("Model features do not match the code: re-run scripts/train_model.py")
    bundle["explainer"] = shap.TreeExplainer(bundle["model"])
    return bundle


def _label(name: str, d: Dossier) -> str:
    if name == "reponse":
        return FEATURE_LABELS[name] if d.reponse_contribuable else "Pas encore de réponse du contribuable"
    if name == "pieces_ratio":
        return f"{FEATURE_LABELS[name]} ({d.pieces_fournies_ratio:.0%})"
    return FEATURE_LABELS[name]


def chef_probas(d: Dossier) -> np.ndarray:
    """Array (n_chefs, 3): P(maintenu), P(réduit), P(annulé) per item."""
    return _bundle()["model"].predict_proba(np.array(dossier_rows(d)))


def expected_recovery(d: Dossier, probas: np.ndarray | None = None) -> tuple[float, np.ndarray]:
    probas = chef_probas(d) if probas is None else probas
    amounts = np.array([c.montant_principal + c.penalites for c in d.notification.chefs])
    shares = probas @ RECOVERY_WEIGHT
    return float((shares * amounts).sum()), shares


def score(d: Dossier, explain: bool = True, top: int = 5) -> ScoreDossier:
    probas = chef_probas(d)
    expected, _ = expected_recovery(d, probas)
    total = d.notification.montant_total or 1.0
    amounts = np.array([c.montant_principal + c.penalites for c in d.notification.chefs])
    weights = amounts / amounts.sum()
    explications: list[ScoreExplication] = []
    if explain:
        X = np.array(dossier_rows(d))
        values = _bundle()["explainer"].shap_values(X)
        # multi-class output: (n_samples, n_features, n_classes) or list per class
        maint = values[:, :, 0] if isinstance(values, np.ndarray) and values.ndim == 3 else values[0]
        contrib = (maint * weights[:, None]).sum(axis=0)
        active = X.max(axis=0) != 0   # only explain with features present in this file
        order = np.argsort(-np.abs(contrib))
        for i in order:
            name = FEATURE_NAMES[i]
            if not active[i] and not name.startswith(("pieces", "reponse")):
                continue
            explications.append(ScoreExplication(facteur=_label(name, d), impact=round(float(contrib[i]), 3)))
            if len(explications) == top:
                break
    return ScoreDossier(
        dossier_id=d.id,
        score_solidite=int(round(100 * expected / total)),
        proba_maintien=round(float((probas[:, 0] * weights).sum()), 3),
        montant_recouvrable_estime=round(expected, 3),
        explications=explications,
    )
