"""Single chokepoint for which columns are safe to feed into the ML model.

FraudFound_P and curation_category are ground-truth/outcome columns and must
never be used as model input, directly or indirectly (Instructions_Set_Reports
.docx section 2). PolicyNumber/RepNumber are row identifiers, not predictive
signal. Make is dropped in favor of the already-engineered, leak-safe
make_fraud_rate to avoid one-hot-encoding a high-cardinality column against
only 100 training rows.
"""
from __future__ import annotations

import pandas as pd

from fraud_detect.config import IDENTIFIER_COLUMNS, LEAKAGE_COLUMNS

DROPPED_FOR_ML = [*LEAKAGE_COLUMNS, *IDENTIFIER_COLUMNS, "Make"]


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in DROPPED_FOR_ML]


def assert_no_leakage(columns: list[str]) -> None:
    leaked = set(columns) & set(LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(f"Leakage columns present in feature set: {leaked}")
