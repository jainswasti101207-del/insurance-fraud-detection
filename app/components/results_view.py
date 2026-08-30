"""Shared rendering of a pipeline result: risk breakdown, evidence,
contradictions, recommendations, and a downloadable WHY-report."""
from __future__ import annotations

import streamlit as st


def _esc(text: str) -> str:
    """Escapes '$' so free-text containing dollar amounts (e.g. Gemini prose,
    narrative excerpts) isn't misinterpreted as LaTeX math by st.markdown."""
    return str(text).replace("$", "\\$")


TIER_COLOR = {
    "LEGITIMATE": "green",
    "MONITOR": "blue",
    "ESCALATE": "orange",
    "HIGH_FRAUD_RISK": "red",
}


def render_result(result) -> None:
    report = result.why_report
    color = TIER_COLOR.get(report.final_status, "gray")

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"**Final Status**\n\n:{color}[{report.final_status.replace('_', ' ')}]")
    col2.metric("Fraud Probability", f"{report.fraud_probability * 100:.1f}%")
    col3.metric("Risk Score", f"{report.risk_score:.1f}/100")
    col4.metric("Confidence", report.confidence)

    st.markdown("#### Why was this claim flagged?")
    if report.top_reasons:
        for reason in report.top_reasons:
            st.markdown(f"- {_esc(reason)}")
    else:
        st.markdown("No significant risk factors identified.")

    with st.expander("Risk score breakdown"):
        for sub in result.risk_sub_scores:
            st.progress(
                min(sub.points / sub.max_points, 1.0) if sub.max_points else 0.0,
                text=f"{sub.name}: {sub.points:.1f}/{sub.max_points}"
                + (f" ({', '.join(sub.flags)})" if sub.flags else ""),
            )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Evidence")
        for k, v in report.supporting_evidence.items():
            st.markdown(f"- **{k}:** {_esc(v)}")
    with col_b:
        st.markdown("#### Contradictions")
        if report.contradictions:
            for c in report.contradictions:
                st.warning(_esc(c))
        else:
            st.markdown("None detected.")

    if result.image_analysis:
        st.markdown("#### Image analysis (Gemini)")
        st.markdown(f"- **Damage severity estimate:** {result.image_analysis.damage_severity_estimate}")
        st.markdown(f"- **Plausibility:** {_esc(result.image_analysis.plausibility_notes)}")
        if result.image_analysis.visual_red_flags:
            for flag in result.image_analysis.visual_red_flags:
                st.warning(_esc(flag))

    if not result.llm_available:
        st.caption("Gemini narrative/image analysis unavailable for this claim - showing rule engine + ML results only.")

    st.markdown("#### What the senior investigator should check")
    for action in report.what_to_check:
        st.markdown(f"- {_esc(action)}")

    with st.expander("Full WHY-report (downloadable)"):
        text = report.to_text()
        st.text(text)
        st.download_button(
            "Download WHY-report (.txt)",
            data=text,
            file_name=f"why_report_{report.claim_id}.txt",
            mime="text/plain",
        )
