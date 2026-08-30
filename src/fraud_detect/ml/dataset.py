"""Builds the ML-ready feature matrix and target, with leakage columns excluded."""
from __future__ import annotations

import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraud_detect.data.load_csv import load_claims
from fraud_detect.features.leakage import assert_no_leakage, get_feature_columns


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    df = load_claims()
    feature_columns = get_feature_columns(df)
    assert_no_leakage(feature_columns)
    X = df[feature_columns].copy()
    y = df["FraudFound_P"].copy()
    return X, y


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric_cols = [c for c in X.columns if is_numeric_dtype(X[c])]
    categorical_cols = [c for c in X.columns if c not in numeric_cols]
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ]
    )


def build_pipeline(estimator, X: pd.DataFrame) -> Pipeline:
    return Pipeline(steps=[("preprocess", build_preprocessor(X)), ("model", estimator)])
