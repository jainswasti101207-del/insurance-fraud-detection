"""Escalation logic (Instructions_Set_Reports.docx §15).

Mandatory triggers force at least ESCALATE regardless of ML probability.
Recommended triggers nudge toward escalation when they co-occur. Explicit
negative guards prevent escalating on any single weak factor alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fraud_detect.rules.scoring import RiskScoreResult


@dataclass
class EscalationResult:
    mandatory_triggered: bool
    reasons: list[str] = field(default_factory=list)
    escalation_score_0_100: float = 0.0
    recommended_factor_count: int = 0


def _is_absent(value: str) -> bool:
    return str(value).strip().lower() == "no"


def evaluate_escalation(
    *,
    police_report_filed: str,
    witness_present: str,
    past_number_of_claims: str,
    fault: str,
    high_value_vehicle_flag: int,
    severity_bucket: str,
    number_of_suppliments: str,
    make_fraud_rate: float,
    dataset_mean_make_fraud_rate: float,
    delay_days: int | None,
    filing_delay_flag: int,
    risk_result: RiskScoreResult,
    ml_probability: float | None,
    ml_high_probability_threshold: float,
    contradiction_count: int,
) -> EscalationResult:
    reasons: list[str] = []
    mandatory = False

    no_evidence = _is_absent(police_report_filed) and _is_absent(witness_present)
    repeat_offender = past_number_of_claims == "more than 4"
    repeat_claims = past_number_of_claims in ("2 to 4", "more than 4")
    policyholder_fault = str(fault).strip().lower() == "policy holder"
    high_value = bool(high_value_vehicle_flag)
    high_severity = severity_bucket == "High"
    delayed = (delay_days is not None and delay_days > 7) or (delay_days is None and bool(filing_delay_flag))
    extensive_repairs = str(number_of_suppliments).strip() == "more than 5"
    high_make_rate = make_fraud_rate > dataset_mean_make_fraud_rate * 1.5

    other_risk_factors = sum(
        [repeat_claims, policyholder_fault, high_value, high_severity, delayed, extensive_repairs]
    )

    # --- Mandatory triggers ---
    if no_evidence and other_risk_factors >= 2:
        mandatory = True
        reasons.append("Complete absence of independent evidence combined with multiple other risk factors")

    if contradiction_count >= 1:
        mandatory = True
        reasons.append("Contradiction between narrative report and structured claim data")

    if high_severity and no_evidence:
        mandatory = True
        reasons.append("Extremely high financial exposure combined with weak evidence")

    if repeat_offender and no_evidence and delayed:
        mandatory = True
        reasons.append("Repeat-claim history, no independent evidence, and delayed reporting together")

    if risk_result.risk_score_0_100 >= 70:
        mandatory = True
        reasons.append(f"Risk score reached a high-risk level ({risk_result.risk_score_0_100}/100)")

    if ml_probability is not None and ml_probability >= ml_high_probability_threshold and risk_result.risk_score_0_100 >= 50:
        mandatory = True
        reasons.append("Model probability is high AND rule-based risk is also high")

    # --- Recommended (soft) triggers: count only, doesn't force escalation alone ---
    recommended_flags = [no_evidence, policyholder_fault, delayed, repeat_claims, high_value, high_severity, extensive_repairs, high_make_rate]
    recommended_count = sum(recommended_flags)
    if not mandatory and recommended_count >= 3:
        reasons.append(f"{recommended_count} recommended risk factors co-occur")

    escalation_score = min(100.0, other_risk_factors * 15 + (25 if no_evidence else 0) + (15 if contradiction_count else 0))

    return EscalationResult(
        mandatory_triggered=mandatory,
        reasons=reasons,
        escalation_score_0_100=round(escalation_score, 1),
        recommended_factor_count=recommended_count,
    )
