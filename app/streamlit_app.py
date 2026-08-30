import streamlit as st

from streamlit_helpers import model_is_ready

st.set_page_config(page_title="Insurance Fraud Investigation Assistant", page_icon="🚗", layout="wide")

st.title("🚗 Insurance Claim Fraud Investigation Assistant")
st.markdown(
    """
A decision-support prototype that analyzes auto-insurance claims (structured data, accident narratives, and
accident photos) to estimate fraud probability, flag claims for human review, and explain **why** - never
issuing a final fraud determination itself.

**Use the sidebar to navigate:**
- **New Claim** - enter a brand-new claim (structured form + optional narrative + optional photo) and get a
  live fraud assessment.
- **Browse Existing Claims** - explore the 100 curated historical claims used to build this system, with
  their real accident reports and photos where available.
- **Evaluation Dashboard** - see how the model performs against ground truth (accuracy, recall, confusion
  matrix, escalation performance, false positive/negative analysis).
"""
)

if not model_is_ready():
    st.error("No trained model found. Run `python -m fraud_detect.ml.train` before using this app.")
else:
    st.success("Model loaded and ready.")

st.markdown("---")
st.caption(
    "This system is a decision-support tool, not a final adjudicator. A human senior investigator makes the "
    "final call on every flagged claim. See docs/limitations.md and docs/ai_use_declaration.md."
)
