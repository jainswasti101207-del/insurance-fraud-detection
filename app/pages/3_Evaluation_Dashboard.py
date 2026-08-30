import json

import pandas as pd
import streamlit as st

from fraud_detect.config import EVALUATION_DIR

st.set_page_config(page_title="Evaluation Dashboard", page_icon="📊", layout="wide")
st.title("Evaluation Dashboard")
st.caption(
    "Reads precomputed evaluation artifacts (run `python -m evaluation.run_full_evaluation` to regenerate) - "
    "does not call Gemini or recompute live on every page load."
)

metrics_path = EVALUATION_DIR / "metrics.json"
if not metrics_path.exists():
    st.error("No evaluation report found. Run `python -m evaluation.run_full_evaluation` first.")
    st.stop()

with open(metrics_path) as f:
    metrics = json.load(f)

st.info(metrics["probability_source"])
st.warning(metrics["small_sample_caveat"])

st.markdown("### ML Model Performance (out-of-fold cross-validation)")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Accuracy", metrics["accuracy"])
c2.metric("Precision", metrics["precision"])
c3.metric("Recall", metrics["recall"])
c4.metric("F1", metrics["f1"])
c5.metric("ROC-AUC", metrics["roc_auc"])
c6.metric("PR-AUC", metrics["pr_auc"])

st.markdown(
    f"**Fraud detection:** {metrics['n_detected']}/{metrics['n_actual_fraud']} actual fraud claims detected, "
    f"{metrics['n_missed']} missed, {metrics['n_false_positives']} false positives "
    f"(false positive rate: {metrics['false_positive_rate']})."
)

cm_path = EVALUATION_DIR / "confusion_matrix.png"
if cm_path.exists():
    st.image(str(cm_path), width=350)

st.markdown("---")
st.markdown("### Escalation Performance")
esc_path = EVALUATION_DIR / "escalation_performance.md"
if esc_path.exists():
    st.markdown(esc_path.read_text(encoding="utf-8").replace("$", "\\$"))

st.markdown("---")
st.markdown("### Per-Claim Predictions")
per_claim_path = EVALUATION_DIR / "per_claim_predictions.csv"
if per_claim_path.exists():
    df = pd.read_csv(per_claim_path)
    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.markdown("### False Positive / False Negative Analysis")
fp_fn_path = EVALUATION_DIR / "fp_fn_analysis.md"
if fp_fn_path.exists():
    st.markdown(fp_fn_path.read_text(encoding="utf-8").replace("$", "\\$"))

st.markdown("---")
st.markdown("### Model Comparison (cross-validated)")
cv_path = EVALUATION_DIR / "cv_model_comparison.json"
if cv_path.exists():
    with open(cv_path) as f:
        cv = json.load(f)
    st.markdown(f"**Chosen model:** {cv['chosen_model']} ({cv['n_splits']}-fold stratified CV)")
    st.dataframe(pd.DataFrame(cv["results"]).T, use_container_width=True)
