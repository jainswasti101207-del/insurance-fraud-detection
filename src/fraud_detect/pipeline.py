"""Single orchestration entrypoint: claim -> features -> rules -> ml -> llm(optional) -> decision -> why_report.

Used by both the Streamlit app and the batch evaluation script, so every
caller runs the exact same fraud-scoring logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from fraud_detect.decision.fusion import fuse
from fraud_detect.decision.why_report import WhyReport, build_why_report
from fraud_detect.features.consistency_check import check_consistency
from fraud_detect.features.derive import date_to_fields, derive_engineered_fields
from fraud_detect.features.engineer import get_dataset_mean_make_fraud_rate, get_make_fraud_rate_table
from fraud_detect.features.narrative_dates import extract_filing_delay_days
from fraud_detect.llm.explanation import draft_explanation
from fraud_detect.llm.image_analysis import analyze_image, analyze_image_bytes
from fraud_detect.llm.narrative_analysis import analyze_narrative
from fraud_detect.llm.schemas import ImageAnalysis, NarrativeAnalysis
from fraud_detect.ml.model_store import load_model, load_model_card, load_thresholds
from fraud_detect.rules.escalation import evaluate_escalation
from fraud_detect.rules.scoring import total_risk_score


@dataclass
class ClaimInput:
    """Unified claim representation for both historical replay and brand-new claims."""

    claim_id: str
    policy_number: str
    raw_fields: dict  # all raw CSV-schema fields (Month, Make, Fault, PoliceReportFiled, ...)
    spreadsheet_row: int | None = None
    narrative_text: str | None = None
    image_path: str | None = None
    image_bytes: tuple[bytes, str] | None = None  # (bytes, mime_type) for live uploads
    accident_date: date | None = None
    claim_date: date | None = None
    engineered_fields: dict | None = None  # if already known (historical claims: use CSV values as-is)
    cached_gemini_result: dict | None = None  # precomputed {"narrative_analysis": {...}, "image_analysis": {...}}


@dataclass
class PipelineResult:
    why_report: WhyReport
    risk_sub_scores: list
    contradictions: list[str]
    narrative_analysis: object | None
    image_analysis: object | None
    llm_available: bool


def _resolve_delay_days(claim: ClaimInput) -> int | None:
    if claim.accident_date and claim.claim_date:
        return (claim.claim_date - claim.accident_date).days
    if claim.narrative_text:
        return extract_filing_delay_days(claim.narrative_text)
    return None


def _build_feature_row(structured: dict, feature_columns: list[str]) -> pd.DataFrame:
    row = {col: structured.get(col) for col in feature_columns}
    return pd.DataFrame([row])


def run_pipeline(claim: ClaimInput, use_llm: bool = True) -> PipelineResult:
    raw = dict(claim.raw_fields)
    if claim.accident_date:
        raw.update(date_to_fields(claim.accident_date))
    if claim.claim_date:
        raw["MonthClaimed"] = date_to_fields(claim.claim_date)["Month"]
        raw["DayOfWeekClaimed"] = date_to_fields(claim.claim_date)["DayOfWeek"]
        raw["WeekOfMonthClaimed"] = date_to_fields(claim.claim_date)["WeekOfMonth"]

    delay_days = _resolve_delay_days(claim)

    if claim.engineered_fields is not None:
        structured = {**raw, **claim.engineered_fields}
    else:
        engineered = derive_engineered_fields(raw, delay_days, get_make_fraud_rate_table())
        structured = {**raw, **engineered}

    dataset_mean_rate = get_dataset_mean_make_fraud_rate()

    risk_result = total_risk_score(
        police_report_filed=structured["PoliceReportFiled"],
        witness_present=structured["WitnessPresent"],
        past_number_of_claims=structured["PastNumberOfClaims"],
        delay_days=delay_days,
        filing_delay_flag=structured["filing_delay_flag"],
        fault=structured["Fault"],
        severity_bucket=structured["severity_bucket"],
        high_value_vehicle_flag=structured["high_value_vehicle_flag"],
        number_of_suppliments=structured["NumberOfSuppliments"],
        make_fraud_rate=structured["make_fraud_rate"],
        dataset_mean_make_fraud_rate=dataset_mean_rate,
    )

    if claim.narrative_text:
        deterministic_contradictions = check_consistency(structured, claim.narrative_text)
        contradiction_details = [c.detail for c in deterministic_contradictions]
    else:
        contradiction_details = []

    narrative_result = None
    image_result = None
    llm_available = False
    if claim.cached_gemini_result is not None:
        cached_narrative = claim.cached_gemini_result.get("narrative_analysis")
        cached_image = claim.cached_gemini_result.get("image_analysis")
        narrative_result = NarrativeAnalysis(**cached_narrative) if cached_narrative else None
        image_result = ImageAnalysis(**cached_image) if cached_image else None
        llm_available = narrative_result is not None or image_result is not None
    elif use_llm:
        if claim.narrative_text:
            narrative_result = analyze_narrative(structured, claim.narrative_text)
        if claim.image_path:
            image_result = analyze_image(claim.image_path, structured)
        elif claim.image_bytes:
            image_result = analyze_image_bytes(claim.image_bytes[0], claim.image_bytes[1], structured)
        llm_available = narrative_result is not None or image_result is not None

    if narrative_result:
        for c in narrative_result.contradictions:
            if c not in contradiction_details:
                contradiction_details.append(c)
    if image_result and image_result.visual_red_flags:
        for c in image_result.visual_red_flags:
            if c not in contradiction_details:
                contradiction_details.append(c)

    model_pipeline = load_model()
    thresholds = load_thresholds()
    feature_columns = load_model_card()["feature_columns"]
    X_row = _build_feature_row(structured, feature_columns)
    ml_probability = float(model_pipeline.predict_proba(X_row)[0, 1])

    escalation_result = evaluate_escalation(
        police_report_filed=structured["PoliceReportFiled"],
        witness_present=structured["WitnessPresent"],
        past_number_of_claims=structured["PastNumberOfClaims"],
        fault=structured["Fault"],
        high_value_vehicle_flag=structured["high_value_vehicle_flag"],
        severity_bucket=structured["severity_bucket"],
        number_of_suppliments=structured["NumberOfSuppliments"],
        make_fraud_rate=structured["make_fraud_rate"],
        dataset_mean_make_fraud_rate=dataset_mean_rate,
        delay_days=delay_days,
        filing_delay_flag=structured["filing_delay_flag"],
        risk_result=risk_result,
        ml_probability=ml_probability,
        ml_high_probability_threshold=thresholds["escalate_below"],
        contradiction_count=len(contradiction_details),
    )

    fusion_result = fuse(
        ml_probability=ml_probability,
        thresholds=thresholds,
        risk_result=risk_result,
        escalation_result=escalation_result,
    )

    llm_sections = None
    if use_llm and llm_available and claim.cached_gemini_result is None:
        # Skipped when replaying a historical claim from the precomputed cache
        # (build_gemini_cache.py) - no live Gemini call needed for browsing.
        llm_sections = draft_explanation(
            structured=structured,
            risk_score=risk_result.risk_score_0_100,
            risk_flags=risk_result.flags,
            ml_probability=ml_probability,
            escalation_reasons=escalation_result.reasons,
            narrative_text=claim.narrative_text or "",
            contradictions=contradiction_details,
        )

    supporting_evidence = {
        "Police report": structured["PoliceReportFiled"],
        "Witness": structured["WitnessPresent"],
        "Evidence score": structured["evidence_score"],
        "Filing delay (days)": delay_days if delay_days is not None else "unknown",
        "Past claims": structured["PastNumberOfClaims"],
        "Fault": structured["Fault"],
        "Vehicle value (midpoint)": structured["vehicle_price_midpoint"],
        "Severity": structured["severity_bucket"],
        "Supplementary repairs": structured["NumberOfSuppliments"],
        "Make fraud rate": round(float(structured["make_fraud_rate"]), 4),
    }

    if llm_sections:
        fusion_result.top_reasons = llm_sections.top_reasons or fusion_result.top_reasons
        narrative_evidence = llm_sections.narrative_evidence or (narrative_result.summary if narrative_result else "")
    else:
        narrative_evidence = narrative_result.summary if narrative_result else (claim.narrative_text or "")

    why_report = build_why_report(
        claim_id=claim.claim_id,
        spreadsheet_row=claim.spreadsheet_row,
        policy_number=claim.policy_number,
        fusion_result=fusion_result,
        supporting_evidence=supporting_evidence,
        narrative_evidence=narrative_evidence,
        contradictions=contradiction_details,
    )
    if llm_sections and llm_sections.what_to_check:
        why_report.what_to_check = llm_sections.what_to_check

    return PipelineResult(
        why_report=why_report,
        risk_sub_scores=risk_result.sub_scores,
        contradictions=contradiction_details,
        narrative_analysis=narrative_result,
        image_analysis=image_result,
        llm_available=llm_available,
    )
