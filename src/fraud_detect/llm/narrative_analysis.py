"""Text-only Gemini call: narrative summary + contradiction candidates.

Runs alongside (not instead of) the deterministic features/consistency_check.py.
Agreement between the two raises confidence in a detected contradiction.
"""
from __future__ import annotations

from fraud_detect.llm.gemini_client import call_gemini_json
from fraud_detect.llm.schemas import NarrativeAnalysis
from fraud_detect.llm.system_prompt import BASE_SYSTEM_PROMPT

PROMPT_TEMPLATE = """Analyze this insurance claim's narrative report against its structured data.

STRUCTURED CLAIM DATA (JSON):
{structured_json}

NARRATIVE ACCIDENT REPORT:
{narrative_text}

Respond with JSON matching this schema:
{{"summary": "1-3 sentence factual summary", "contradictions": ["specific disagreement between narrative and structured data, if any"], "notable_facts": ["facts relevant to fraud risk: evidence, delays, history"]}}

If there are no contradictions, return an empty list for contradictions."""


def analyze_narrative(structured: dict, narrative_text: str) -> NarrativeAnalysis | None:
    if not narrative_text:
        return None
    import json

    prompt = PROMPT_TEMPLATE.format(structured_json=json.dumps(structured, default=str), narrative_text=narrative_text)
    try:
        result = call_gemini_json([prompt], BASE_SYSTEM_PROMPT)
        return NarrativeAnalysis(**result)
    except Exception:  # noqa: BLE001 - graceful degradation
        return None
