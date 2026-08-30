import streamlit as st

from components.claim_form import render_claim_form
from components.results_view import render_result
from fraud_detect.pipeline import ClaimInput, run_pipeline
from streamlit_helpers import model_is_ready

st.set_page_config(page_title="New Claim", page_icon="🚗", layout="wide")
st.title("New Claim Assessment")
st.caption(
    "Enter a brand-new claim's details. Narrative and photo are optional - the system runs the rule engine "
    "and ML model on structured data alone if neither is provided, and adds Gemini narrative/image analysis "
    "live when they are."
)

if not model_is_ready():
    st.error("No trained model found. Run `python -m fraud_detect.ml.train` first.")
    st.stop()

submission = render_claim_form()

if submission:
    image_bytes = None
    if submission["image_file"] is not None:
        image_bytes = (submission["image_file"].getvalue(), submission["image_file"].type)
        st.image(submission["image_file"], caption="Uploaded photo", width=300)

    claim = ClaimInput(
        claim_id=f"NEW-{submission['accident_date'].isoformat()}",
        policy_number="NEW (not yet assigned)",
        raw_fields=submission["raw_fields"],
        narrative_text=submission["narrative_text"],
        image_bytes=image_bytes,
        accident_date=submission["accident_date"],
        claim_date=submission["claim_date"],
    )

    with st.spinner("Analyzing claim (rule engine + ML model + Gemini)..."):
        result = run_pipeline(claim, use_llm=True)

    st.markdown("---")
    render_result(result)
