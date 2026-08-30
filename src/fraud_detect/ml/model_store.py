"""Persist/load the chosen model pipeline, model card, and tier thresholds."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import sklearn

from fraud_detect.config import MODEL_CARD_PATH, MODEL_PATH, THRESHOLDS_PATH


def save_model(pipeline, model_name: str, cv_metrics: dict, feature_columns: list[str], thresholds: dict) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    card = {
        "model_name": model_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "feature_columns": feature_columns,
        "cv_metrics": cv_metrics,
        "excluded_columns_note": "FraudFound_P and curation_category are ground-truth labels, "
        "never used as model input. PolicyNumber/RepNumber/Make also excluded (identifiers / "
        "high-cardinality with only 100 rows; make_fraud_rate used instead).",
        "n_training_rows": 100,
        "n_positive_class": None,
        "small_sample_caveat": "Trained on only 100 rows with 11 positive (fraud) examples. "
        "Cross-validated metrics carry high variance and should not be over-interpreted; "
        "see docs/limitations.md.",
    }
    with open(MODEL_CARD_PATH, "w") as f:
        json.dump(card, f, indent=2)

    with open(THRESHOLDS_PATH, "w") as f:
        json.dump(thresholds, f, indent=2)


def load_model():
    return joblib.load(MODEL_PATH)


def load_thresholds() -> dict:
    with open(THRESHOLDS_PATH) as f:
        return json.load(f)


def load_model_card() -> dict:
    with open(MODEL_CARD_PATH) as f:
        return json.load(f)
