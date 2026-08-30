"""Trains and cross-validates candidate models (Instructions_Set_Reports.docx §11-14).

100 rows / 11 positives is too small for a single train/test split to be
meaningful (§13), so we use StratifiedKFold(5) - the largest split that still
keeps ~2 positive examples per fold - and report mean/std across folds. Final
model is refit on the full 100 rows for deployment; its out-of-fold
predictions (not its in-sample predictions) are what the reported metrics and
tier thresholds are based on, since in-sample metrics on n=100 would be
wildly optimistic.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from fraud_detect.config import EVALUATION_DIR, RANDOM_STATE
from fraud_detect.ml.dataset import build_pipeline, load_dataset
from fraud_detect.ml.evaluate import compute_metrics
from fraud_detect.ml.model_store import save_model
from fraud_detect.ml.threshold import recommend_tier_thresholds

N_SPLITS = 5


def _candidate_models(scale_pos_weight: float) -> dict:
    models = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE
        ),
        "decision_tree": DecisionTreeClassifier(
            class_weight="balanced", max_depth=4, random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced", n_estimators=200, max_depth=5, random_state=RANDOM_STATE
        ),
    }
    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=150,
            max_depth=3,
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_STATE,
            eval_metric="logloss",
        )
    except ImportError:
        pass
    return models


def _oof_probabilities(pipeline, X, y, cv) -> np.ndarray:
    proba = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")
    return proba[:, 1]


def train_and_evaluate() -> dict:
    X, y = load_dataset()
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    scale_pos_weight = n_neg / max(n_pos, 1)

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    results = {}
    oof_by_model = {}
    for name, estimator in _candidate_models(scale_pos_weight).items():
        pipeline = build_pipeline(estimator, X)
        oof_prob = _oof_probabilities(pipeline, X, y, cv)
        metrics = compute_metrics(y.values, oof_prob)
        results[name] = {
            "accuracy": round(metrics.accuracy, 3),
            "precision": round(metrics.precision, 3),
            "recall": round(metrics.recall, 3),
            "f1": round(metrics.f1, 3),
            "roc_auc": round(metrics.roc_auc, 3) if metrics.roc_auc == metrics.roc_auc else None,
            "pr_auc": round(metrics.pr_auc, 3) if metrics.pr_auc == metrics.pr_auc else None,
            "false_positive_rate": round(metrics.false_positive_rate, 3),
            "n_actual_fraud": metrics.n_actual_fraud,
            "n_detected": metrics.n_detected,
            "n_missed": metrics.n_missed,
        }
        oof_by_model[name] = oof_prob

    # Model selection: PR-AUC is more informative than ROC-AUC under heavy
    # class imbalance (§12); ties broken by recall since missed fraud is framed
    # as costlier than wasted investigation time throughout the instructions.
    best_name = max(results, key=lambda n: (results[n]["pr_auc"] or 0, results[n]["recall"]))
    best_oof_prob = oof_by_model[best_name]

    thresholds = recommend_tier_thresholds(y.values, best_oof_prob)

    # Persist out-of-fold probabilities for the chosen model. The deployed
    # model below is refit on ALL 100 rows, so its own predict_proba on those
    # same rows is in-sample and would look artificially perfect; the honest
    # generalization estimate for the evaluation report is these oof values,
    # not the deployed model's in-sample output (see evaluation/run_full_evaluation.py).
    import pandas as pd

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "csv_row_index": X.index,
            "oof_probability": best_oof_prob,
            "actual_fraud": y.values,
        }
    ).to_csv(EVALUATION_DIR / "oof_predictions.csv", index=False)

    # Refit the chosen model on the full dataset for deployment.
    best_estimator = _candidate_models(scale_pos_weight)[best_name]
    final_pipeline = build_pipeline(best_estimator, X)
    final_pipeline.fit(X, y)

    save_model(
        final_pipeline,
        model_name=best_name,
        cv_metrics=results,
        feature_columns=list(X.columns),
        thresholds=thresholds,
    )

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVALUATION_DIR / "cv_model_comparison.json", "w") as f:
        json.dump({"chosen_model": best_name, "n_splits": N_SPLITS, "results": results}, f, indent=2)

    return {"chosen_model": best_name, "results": results, "thresholds": thresholds}


def main() -> None:
    summary = train_and_evaluate()
    print(f"Chosen model: {summary['chosen_model']}")
    for name, m in summary["results"].items():
        print(f"  {name}: precision={m['precision']} recall={m['recall']} f1={m['f1']} pr_auc={m['pr_auc']} roc_auc={m['roc_auc']}")
    print(f"Tier thresholds: {summary['thresholds']['legitimate_below']} / {summary['thresholds']['monitor_below']} / {summary['thresholds']['escalate_below']}")


if __name__ == "__main__":
    main()
