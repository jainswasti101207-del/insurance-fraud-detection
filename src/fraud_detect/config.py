"""Central paths, constants, and secret loading for the fraud-detection system."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
EVALUATION_DIR = PROJECT_ROOT / "evaluation" / "evaluation_report"

CSV_PATH = RAW_DIR / "curated_100_claims_with_ground_truth.csv"
REPORTS_DOCX_PATH = RAW_DIR / "Accident_Reports.docx"
IMAGES_DIR = RAW_DIR / "Insurance_Fraud_Investigation_Images"

CLAIM_MAPPING_PATH = PROCESSED_DIR / "claim_mapping.csv"
NARRATIVES_PATH = PROCESSED_DIR / "narratives_extracted.csv"
GEMINI_CACHE_PATH = PROCESSED_DIR / "gemini_cache.json"

MODEL_PATH = MODELS_DIR / "model.joblib"
PREPROCESSOR_PATH = MODELS_DIR / "preprocessor.joblib"
MODEL_CARD_PATH = MODELS_DIR / "model_card.json"
THRESHOLDS_PATH = MODELS_DIR / "thresholds.json"

# Report N maps to CSV row N-2 (0-based). Verified against report 16 (Accura, 79yo,
# repeat-offender narrative) matching csv row index 14 exactly.
REPORT_NUMBER_OFFSET = 2

LEAKAGE_COLUMNS = ["FraudFound_P", "curation_category"]
IDENTIFIER_COLUMNS = ["PolicyNumber", "RepNumber"]

RANDOM_STATE = 42

load_dotenv(PROJECT_ROOT / ".env")


def get_api_key() -> str | None:
    """Read GEMINI_API_KEY from the environment (local .env) or Streamlit
    secrets (deployed). Env var is checked first so non-Streamlit contexts
    (scripts, tests, the training pipeline) never pay the cost of importing
    streamlit just to discover it isn't running."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    try:
        import streamlit as st  # noqa: PLC0415

        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return None
