"""Cached resource loading shared across all Streamlit pages."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from fraud_detect.config import CLAIM_MAPPING_PATH, CSV_PATH, GEMINI_CACHE_PATH, MODEL_PATH
from fraud_detect.data.extract_narratives import extract_narratives
from fraud_detect.ml.model_store import load_model, load_model_card, load_thresholds


@st.cache_resource
def get_model():
    return load_model()


@st.cache_resource
def get_thresholds() -> dict:
    return load_thresholds()


@st.cache_resource
def get_model_card() -> dict:
    return load_model_card()


@st.cache_data
def get_claims_df() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH)


@st.cache_data
def get_narratives_df() -> pd.DataFrame:
    return extract_narratives().set_index("csv_row_index")


@st.cache_data
def get_mapping_df() -> pd.DataFrame:
    return pd.read_csv(CLAIM_MAPPING_PATH).set_index("csv_row_index")


@st.cache_data
def get_gemini_cache() -> dict:
    if not GEMINI_CACHE_PATH.exists():
        return {}
    with open(GEMINI_CACHE_PATH) as f:
        return json.load(f)


def model_is_ready() -> bool:
    return MODEL_PATH.exists()
