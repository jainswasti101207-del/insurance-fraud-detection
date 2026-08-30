# AI-Use Declaration

## Development of this project

This project was designed and built with the help of an AI coding assistant, working interactively with the
student. The assistant was used to:

- explore and understand the provided dataset, accident reports, and instruction documents;
- design the system architecture (rule engine + ML model + Gemini multimodal layer + Streamlit UI);
- write the Python source code, tests, and evaluation scripts;
- write this documentation.

All design decisions, data facts, and evaluation results in this documentation were verified against the
actual project files and code (not assumed) - for example, the report-to-row mapping rule, the discovery
that `days_policy_claim_numeric`/`filing_delay_flag` are near-constant in this sample, and the correction
that `Instructions_Set_Images.docx`'s "report card" assumption doesn't match the real (photographic)
images, were all confirmed by directly inspecting the data before being encoded into the system.

## AI used within the running system

The deployed application itself uses **Google Gemini** (`gemini-2.5-flash`) for three specific,
clearly-scoped purposes - it is **not** the source of the numeric fraud probability or risk score:

1. **Narrative analysis** (`src/fraud_detect/llm/narrative_analysis.py`): summarizes the accident report
   text and flags candidate contradictions against the structured claim data, as a secondary check
   alongside the deterministic keyword-based contradiction detector
   (`src/fraud_detect/features/consistency_check.py`).
2. **Image analysis** (`src/fraud_detect/llm/image_analysis.py`): assesses visible damage severity and
   plausibility in an accident photo. Scoped deliberately as photo interpretation, not data extraction -
   see the "corrected assumption" note in `docs/data_documentation.md`.
3. **Explanation drafting** (`src/fraud_detect/llm/explanation.py`): writes the natural-language "top
   reasons" / "narrative evidence" / "what to check" sections of the WHY-report in a FACT/INFERENCE/
   RECOMMENDATION style, grounded only in the rule engine's, ML model's, and narrative/image analysis's
   actual output - it is explicitly instructed never to invent facts, never to use accusatory language, and
   never to treat demographic fields as fraud determinants (`src/fraud_detect/llm/system_prompt.py`).

**The fraud probability (from the trained ML model) and the risk/escalation scores (from the deterministic
rule engine) are computed entirely without Gemini**, and the system produces a complete, auditable
WHY-report even when Gemini is unavailable (rate-limited, no API key, or network failure) via documented
deterministic fallbacks in `src/fraud_detect/decision/why_report.py`.

Gemini output is never treated as ground truth: `FraudFound_P`/`curation_category` are never included in
any prompt sent to Gemini, and its final classification of a claim is always one of the non-accusatory,
decision-support labels required by `Instructions_Set_Reports.docx` &sect;19 (never "this is fraud" or
"the claimant is lying").
