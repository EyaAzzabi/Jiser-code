"""Train the per-item outcome model and measure what JISER's triage would bring.

Model: XGBoost, 3 classes per reassessment item (maintenu / réduit / annulé).
From it we derive, per file, the expected recoverable amount and a 0-100 solidity score.

Evaluation (held-out files, split by file so no leakage between items of the same file):
  * AUC of "item upheld" (maintenu vs other)
  * AUC of "file mostly recovered" (>= 50 % of the notified amount)
  * Triage simulation: with capacity for 20 % of files, amount recovered when files are
    picked by JISER's priority vs oldest-first (FIFO) vs largest-amount-first.

Outputs: models/chef_model.joblib, models/metrics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import Dossier  # noqa: E402
from app.services.features import FEATURE_NAMES, dossier_rows  # noqa: E402

CLASSES = ["maintenu", "reduit", "annule"]
RECOVERY_WEIGHT = np.array([1.0, 0.5, 0.0])   # expected share recovered per class
CAPACITY = 0.20


def load_closed() -> list[Dossier]:
    raw = json.loads((ROOT / "data" / "synthetic" / "dossiers.json").read_text(encoding="utf-8"))
    return [Dossier.model_validate(d) for d in raw if d["statut"] == "cloture"]


def build(dossiers: list[Dossier]):
    X, y, groups, amounts = [], [], [], []
    for gi, d in enumerate(dossiers):
        issue_by_chef = {i.chef_id: i.issue for i in d.issues}
        for row, c in zip(dossier_rows(d), d.notification.chefs):
            X.append(row)
            y.append(CLASSES.index(issue_by_chef[c.id]))
            groups.append(gi)
            amounts.append(c.montant_principal + c.penalites)
    return np.array(X), np.array(y), np.array(groups), np.array(amounts)


def main() -> None:
    dossiers = load_closed()
    X, y, groups, amounts = build(dossiers)
    split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    tr, te = next(split.split(X, y, groups))

    model = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.06, subsample=0.9,
                          colsample_bytree=0.9, objective="multi:softprob", eval_metric="mlogloss",
                          random_state=42)
    model.fit(X[tr], y[tr])
    proba = model.predict_proba(X[te])

    auc_item = roc_auc_score((y[te] == 0).astype(int), proba[:, 0])
    acc_item = accuracy_score(y[te], proba.argmax(1))

    # file-level aggregation on the test files
    exp_share = proba @ RECOVERY_WEIGHT
    test_groups = groups[te]
    files = []
    for g in np.unique(test_groups):
        m = test_groups == g
        d = dossiers[g]
        total = d.notification.montant_total
        files.append({
            "expected": float((exp_share[m] * amounts[te][m]).sum()),
            "total": total,
            "actual": d.montant_recouvre or 0.0,
            "date": d.notification.date_notification.toordinal(),
        })
    exp_ratio = np.array([f["expected"] / f["total"] for f in files])
    act_ratio = np.array([f["actual"] / f["total"] for f in files])
    auc_file = roc_auc_score((act_ratio >= 0.5).astype(int), exp_ratio)
    mae_ratio = float(np.abs(exp_ratio - act_ratio).mean())

    k = max(1, int(len(files) * CAPACITY))

    def recovered(order_key, reverse=True):
        picked = sorted(files, key=order_key, reverse=reverse)[:k]
        return sum(f["actual"] for f in picked)

    jiser = recovered(lambda f: f["expected"])
    fifo = recovered(lambda f: f["date"], reverse=False)
    biggest = recovered(lambda f: f["total"])
    metrics = {
        "n_dossiers_train": int(len(np.unique(groups[tr]))),
        "n_dossiers_test": len(files),
        "n_chefs_test": int(len(te)),
        "auc_chef_maintenu": round(float(auc_item), 3),
        "accuracy_chef_3_classes": round(float(acc_item), 3),
        "auc_dossier_recouvre_50pct": round(float(auc_file), 3),
        "mae_taux_recouvrement": round(mae_ratio, 3),
        "triage": {
            "capacite": f"{int(CAPACITY * 100)} % des dossiers",
            "recouvre_jiser": round(jiser),
            "recouvre_fifo": round(fifo),
            "recouvre_plus_gros_montants": round(biggest),
            "gain_vs_fifo_pct": round(100 * (jiser / fifo - 1), 1),
            "gain_vs_plus_gros_pct": round(100 * (jiser / biggest - 1), 1),
        },
        "note": "Mesuré sur des données synthétiques (règles métier + bruit). À réentraîner sur l'historique réel.",
    }

    # Final model on all closed files
    model.fit(X, y)
    out = ROOT / "models"
    out.mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_NAMES, "classes": CLASSES}, out / "chef_model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
