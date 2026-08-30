import streamlit as st

from components.results_view import render_result
from fraud_detect.config import RAW_DIR
from fraud_detect.pipeline import ClaimInput, run_pipeline
from streamlit_helpers import get_claims_df, get_gemini_cache, get_mapping_df, get_narratives_df, model_is_ready

st.set_page_config(page_title="Browse Existing Claims", page_icon="📋", layout="wide")
st.title("Browse Existing Claims")
st.caption(
    "The 100 curated historical claims used to build this system. Gemini narrative/image analysis is "
    "precomputed and cached for these, so browsing never makes a live API call."
)

if not model_is_ready():
    st.error("No trained model found. Run `python -m fraud_detect.ml.train` first.")
    st.stop()

claims = get_claims_df()
narratives = get_narratives_df()
mapping = get_mapping_df()
gemini_cache = get_gemini_cache()

col1, col2 = st.columns([1, 3])
with col1:
    row_index = st.selectbox(
        "Select a claim (spreadsheet row)",
        options=list(range(len(claims))),
        format_func=lambda i: f"Row {i} - Policy {claims.iloc[i]['PolicyNumber']}"
        + (" 📷" if mapping.loc[i, "has_image"] else ""),
    )

row = claims.iloc[row_index]
narrative_text = narratives.loc[row_index, "narrative_text"]
m = mapping.loc[row_index]

with col2:
    st.markdown(f"**Make:** {row['Make']} | **Accident Area:** {row['AccidentArea']} | **Fault:** {row['Fault']}")
    escaped_narrative = narrative_text.replace("$", "\\$")
    st.markdown(f"**Narrative:** {escaped_narrative}")
    if m["has_image"]:
        st.image(str(RAW_DIR / m["image_path"]), caption=m["image_path"], width=400)

claim = ClaimInput(
    claim_id=f"CLM-{row_index}",
    policy_number=row["PolicyNumber"],
    raw_fields=row.to_dict(),
    spreadsheet_row=row_index,
    narrative_text=narrative_text,
    engineered_fields=row.to_dict(),
    cached_gemini_result=gemini_cache.get(str(row_index)),
)

with st.spinner("Running rule engine + ML model..."):
    result = run_pipeline(claim, use_llm=True)

st.markdown("---")
render_result(result)

with st.expander("Ground truth (evaluation only - not shown to the scoring engine above)"):
    st.markdown(f"- **FraudFound_P:** {row['FraudFound_P']}")
    st.markdown(f"- **curation_category:** {row['curation_category']}")
