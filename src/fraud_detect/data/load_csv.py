"""Load and schema-validate the curated claims CSV."""
from __future__ import annotations

import pandas as pd

from fraud_detect.config import CSV_PATH, LEAKAGE_COLUMNS

EXPECTED_COLUMN_COUNT = 57


def load_claims() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    if df.shape[1] != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_COLUMN_COUNT} columns in {CSV_PATH.name}, got {df.shape[1]}"
        )
    for col in LEAKAGE_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Expected leakage column '{col}' missing from CSV — schema changed?")
    df.index.name = "csv_row_index"
    return df
