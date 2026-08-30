"""Drafts the WHY-report prose sections in FACT/INFERENCE/RECOMMENDATION
style (Instructions_Set_Reports.docx §16-18). Falls back to None (caller uses
the deterministic template from decision/why_report.py) if Gemini is
unavailable."""
from __future__ import annotations

import json

from fraud_detect.llm.gemini_client import call_gemini_json
from fraud_detect.llm.schemas import WhyReportSections
from fraud_detect.llm.system_prompt import BASE_SYSTEM_PROMPT

PROMPT_TEMPLATE = """Draft the explanation sections of a fraud-investigation WHY-report for this claim.

STRUCTURED DATA (JSON): {structured_json}
RULE-BASED RISK SCORE: {risk_score}/100 (contributing flags: {risk_flags})
ML FRAUD PROBABILITY: {ml_probability}
ESCALATION TRIGGERS: {escalation_reasons}
NARRATIVE REPORT: {narrative_text}
DETECTED CONTRADICTIONS: {contradictions}

Write TOP REASONS (3-5 bullet points, each stating a FACT and explaining WHY it matters and HOW it \
interacts with other factors - not just "score is high"). Write NARRATIVE_EVIDENCE summarizing only facts \
actually present above. Write WHAT_TO_CHECK as concrete, specific investigation actions (never "investigate \
further").

Respond with JSON matching this schema:
{{"top_reasons": ["..."], "narrative_evidence": "...", "what_to_check": ["..."]}}"""


def draft_explanation(
    *,
    structured: dict,
    risk_score: float,
    risk_flags: list[str],
    ml_probability: float,
    escalation_reasons: list[str],
    narrative_text: str,
    contradictions: list[str],
) -> WhyReportSections | None:
    prompt = PROMPT_TEMPLATE.format(
        structured_json=json.dumps(structured, default=str),
        risk_score=risk_score,
        risk_flags=", ".join(risk_flags) or "none",
        ml_probability=ml_probability,
        escalation_reasons=", ".join(escalation_reasons) or "none",
        narrative_text=narrative_text or "Not provided.",
        contradictions=", ".join(contradictions) or "none",
    )
    try:
        result = call_gemini_json([prompt], BASE_SYSTEM_PROMPT)
        return WhyReportSections(**result)
    except Exception:  # noqa: BLE001 - graceful degradation, caller uses deterministic fallback
        return None
