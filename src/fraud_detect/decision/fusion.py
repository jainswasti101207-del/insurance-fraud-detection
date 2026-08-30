"""Combines rule score + ML probability + escalation triggers into the final
4-tier decision (Instructions_Set_Reports.docx §25).

Fusion algorithm (in order):
1. Start from the ML-probability-driven tier using the persisted threshold
   cut points from ml/threshold.py.
2. Apply mandatory-trigger overrides from rules/escalation.py: any mandatory
   trigger forces the tier to at least ESCALATE, regardless of ML probability.
3. If mandatory triggers fired AND the ML probability is also above the
   escalate cut point, bump to HIGH_FRAUD_RISK (a strong combination of
   independent rule-based and model-based signals reinforcing each other).
Confidence is HIGH when the rule-tier and ML-tier agree, MEDIUM when they're
adjacent, LOW when they disagree by more than one tier.
"""
from __future__ import annotations

from dataclasses import dataclass

TIERS = ["LEGITIMATE", "MONITOR", "ESCALATE", "HIGH_FRAUD_RISK"]


@dataclass
class FusionResult:
    final_tier: str
    fraud_probability: float
    risk_score: float
    escalation_score: float
    confidence: str
    top_reasons: list[str]


def _tier_from_probability(prob: float, thresholds: dict) -> str:
    if prob < thresholds["legitimate_below"]:
        return "LEGITIMATE"
    if prob < thresholds["monitor_below"]:
        return "MONITOR"
    if prob < thresholds["escalate_below"]:
        return "ESCALATE"
    return "HIGH_FRAUD_RISK"


def _tier_from_risk_score(risk_score_0_100: float) -> str:
    if risk_score_0_100 < 25:
        return "LEGITIMATE"
    if risk_score_0_100 < 50:
        return "MONITOR"
    if risk_score_0_100 < 70:
        return "ESCALATE"
    return "HIGH_FRAUD_RISK"


def fuse(
    *,
    ml_probability: float,
    thresholds: dict,
    risk_result,
    escalation_result,
) -> FusionResult:
    ml_tier = _tier_from_probability(ml_probability, thresholds)
    rule_tier = _tier_from_risk_score(risk_result.risk_score_0_100)

    final_tier = ml_tier
    if escalation_result.mandatory_triggered:
        min_index = TIERS.index("ESCALATE")
        if TIERS.index(final_tier) < min_index:
            final_tier = "ESCALATE"
        if ml_probability >= thresholds["escalate_below"]:
            final_tier = "HIGH_FRAUD_RISK"

    ml_index = TIERS.index(ml_tier)
    rule_index = TIERS.index(rule_tier)
    diff = abs(ml_index - rule_index)
    if diff == 0:
        confidence = "High"
    elif diff == 1:
        confidence = "Medium"
    else:
        confidence = "Low"

    reasons = list(dict.fromkeys(escalation_result.reasons + risk_result.flags))[:5]

    return FusionResult(
        final_tier=final_tier,
        fraud_probability=round(ml_probability, 3),
        risk_score=risk_result.risk_score_0_100,
        escalation_score=escalation_result.escalation_score_0_100,
        confidence=confidence,
        top_reasons=reasons,
    )
