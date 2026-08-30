"""Small derived-feature helpers shared by the rule engine and ML pipeline."""
from __future__ import annotations

from functools import lru_cache

from fraud_detect.data.load_csv import load_claims


@lru_cache(maxsize=1)
def get_dataset_mean_make_fraud_rate() -> float:
    df = load_claims()
    return float(df["make_fraud_rate"].mean())


@lru_cache(maxsize=1)
def get_make_fraud_rate_table() -> dict:
    df = load_claims()
    return df.groupby("Make")["make_fraud_rate"].first().to_dict()
