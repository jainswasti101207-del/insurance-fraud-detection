"""Rule-based 0-100 risk score (Instructions_Set_Reports.docx §10).

Each sub-score is an independent, pure, unit-testable function returning
(points, contributing_flags). total_risk_score() sums them and rescales the
raw 0-95 total to 0-100 in one documented step.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fraud_detect.rules import constants as C

NUMBER_OF_SUPPLIMENTS_POINTS = {
    "none": 0,
    "1 to 2": 2,
    "3 to 5": 5,
    "more than 5": 10,
}


@dataclass
class SubScore:
    name: str
    points: float
    max_points: float
    flags: list[str] = field(default_factory=list)


def evidence_risk(police_report_filed: str, witness_present: str) -> SubScore:
    flags = []
    points = 0
    police_absent = str(police_report_filed).strip().lower() == "no"
    witness_absent = str(witness_present).strip().lower() == "no"
    if police_absent:
        points += C.POLICE_ABSENT_POINTS
        flags.append("No police report")
    if witness_absent:
        points += C.WITNESS_ABSENT_POINTS
        flags.append("No witness")
    if police_absent and witness_absent:
        points += C.BOTH_ABSENT_BONUS_POINTS
        flags.append("Complete absence of independent evidence")
    return SubScore("Evidence Risk", min(points, C.EVIDENCE_RISK_CAP), C.EVIDENCE_RISK_CAP, flags)


def claim_history(past_number_of_claims: str) -> SubScore:
    key = str(past_number_of_claims).strip()
    points = C.PAST_CLAIMS_POINTS.get(key, 0)
    flags = [f"Past claims: {key}"] if key not in ("none", "0") else []
    if key == "more than 4":
        flags.append("Repeat offender (more than 4 past claims)")
    return SubScore("Claim History", min(points, C.CLAIM_HISTORY_CAP), C.CLAIM_HISTORY_CAP, flags)


def reporting_behavior(delay_days: int | None, filing_delay_flag: int) -> SubScore:
    flags = []
    if delay_days is not None:
        if delay_days <= C.DELAY_LOW_MAX_DAYS:
            points = C.DELAY_LOW_POINTS
        elif delay_days <= C.DELAY_MODERATE_MAX_DAYS:
            points = C.DELAY_MODERATE_POINTS
            flags.append(f"Moderate filing delay ({delay_days} days)")
        else:
            points = C.DELAY_HIGH_POINTS
            flags.append(f"High filing delay ({delay_days} days)")
    elif filing_delay_flag:
        points = C.DELAY_FLAG_FALLBACK_POINTS
        flags.append("Filing delay flag set (exact delay unknown, using categorical fallback)")
    else:
        points = 0
    return SubScore("Reporting Behavior", min(points, C.DELAY_HIGH_POINTS), C.DELAY_HIGH_POINTS, flags)


def fault_score(fault: str) -> SubScore:
    is_policyholder = str(fault).strip().lower() == "policy holder"
    points = C.POLICYHOLDER_FAULT_POINTS if is_policyholder else C.THIRD_PARTY_FAULT_POINTS
    flags = ["Policyholder at fault"] if is_policyholder else []
    return SubScore("Fault", points, C.POLICYHOLDER_FAULT_POINTS, flags)


def financial_exposure(severity_bucket: str) -> SubScore:
    """Uses the pre-engineered severity_bucket, which already blends vehicle
    value, coverage multiplier, and severity proxy exactly as §10 instructs
    considering ("vehicle value; severity; coverage multiplier; severity
    proxy")."""
    mapping = {"Low": 0, "Medium": 8, "High": 15}
    bucket = str(severity_bucket).strip()
    points = mapping.get(bucket, 0)
    flags = [f"{bucket} severity exposure"] if bucket == "High" else []
    return SubScore("Financial Exposure", points, C.FINANCIAL_EXPOSURE_CAP, flags)


def vehicle_claim_pattern(high_value_vehicle_flag: int, number_of_suppliments: str) -> SubScore:
    flags = []
    points = 0
    if high_value_vehicle_flag:
        points += 5
        flags.append("High-value vehicle")
    supplement_points = NUMBER_OF_SUPPLIMENTS_POINTS.get(str(number_of_suppliments).strip(), 0)
    points += supplement_points
    if supplement_points >= 10:
        flags.append("Extensive supplementary repairs")
    return SubScore("Vehicle/Claim Pattern", min(points, C.VEHICLE_PATTERN_CAP), C.VEHICLE_PATTERN_CAP, flags)


def statistical_risk(make_fraud_rate: float, dataset_mean_rate: float) -> SubScore:
    flags = []
    points = 0
    if make_fraud_rate > dataset_mean_rate:
        # Scale linearly, capped small per §10 ("keep this component small").
        ratio = min(make_fraud_rate / max(dataset_mean_rate, 1e-9), 2.0)
        points = min((ratio - 1.0) * C.STATISTICAL_RISK_CAP, C.STATISTICAL_RISK_CAP)
        if points >= C.STATISTICAL_RISK_CAP * 0.5:
            flags.append("Elevated make fraud rate")
    return SubScore("Statistical Risk", round(points, 2), C.STATISTICAL_RISK_CAP, flags)


@dataclass
class RiskScoreResult:
    sub_scores: list[SubScore]
    raw_total: float
    risk_score_0_100: float
    flags: list[str]


def total_risk_score(
    *,
    police_report_filed: str,
    witness_present: str,
    past_number_of_claims: str,
    delay_days: int | None,
    filing_delay_flag: int,
    fault: str,
    severity_bucket: str,
    high_value_vehicle_flag: int,
    number_of_suppliments: str,
    make_fraud_rate: float,
    dataset_mean_make_fraud_rate: float,
) -> RiskScoreResult:
    sub_scores = [
        evidence_risk(police_report_filed, witness_present),
        claim_history(past_number_of_claims),
        reporting_behavior(delay_days, filing_delay_flag),
        fault_score(fault),
        financial_exposure(severity_bucket),
        vehicle_claim_pattern(high_value_vehicle_flag, number_of_suppliments),
        statistical_risk(make_fraud_rate, dataset_mean_make_fraud_rate),
    ]
    raw_total = sum(s.points for s in sub_scores)
    risk_score_0_100 = round(min(raw_total, C.RAW_SCORE_MAX) / C.RAW_SCORE_MAX * 100, 1)
    flags = [f for s in sub_scores for f in s.flags]
    return RiskScoreResult(sub_scores, raw_total, risk_score_0_100, flags)
