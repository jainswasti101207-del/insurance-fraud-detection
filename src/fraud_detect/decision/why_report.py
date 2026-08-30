"""Assembles the exact §16 WHY-report field layout.

This deterministic version builds SUPPORTING EVIDENCE, TOP REASONS,
CONTRADICTIONS, and WHAT TO CHECK directly from rule/ML/escalation output, so
the system always produces a complete, auditable report even when Gemini is
unavailable. llm/explanation.py enriches NARRATIVE EVIDENCE and adds
FACT/INFERENCE/RECOMMENDATION prose on top of this when available.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Maps an escalation/risk reason substring to a concrete, non-generic
# investigation action (§16: "Do NOT merely say investigate further").
ACTION_MAP = [
    ("No police report", "Verify the accident through available external documentation (dashcam, traffic camera, 911 dispatch log)."),
    ("No witness", "Attempt to independently identify and contact any witnesses named in the claimant's statement."),
    ("Complete absence", "Request additional corroborating documentation before proceeding (repair invoices, photos, dispatch records)."),
    ("Repeat offender", "Review the claimant's full prior claims history for pattern similarity to this incident."),
    ("Past claims", "Cross-check past claims for the same vehicle/policyholder for recurring damage patterns."),
    ("filing delay", "Ask the claimant to explain the reporting delay and verify the timeline against any external records."),
    ("Policyholder at fault", "Compare the claimed fault determination against any available police/witness statements."),
    ("High-value vehicle", "Verify the vehicle's declared value against an independent valuation source."),
    ("severity", "Inspect the vehicle damage in person or via submitted photos and compare to the claimed accident description."),
    ("Extensive supplementary repairs", "Verify itemized repair invoices against the damage described in the claim."),
    ("Elevated make fraud rate", "Treat as a minor contextual signal only; do not use vehicle make as a primary basis for action."),
    ("Contradiction", "Reconcile the specific discrepancy between the narrative report and the structured claim data before proceeding."),
    ("Risk score reached", "Escalate to a senior investigator given the compounding combination of risk factors."),
    ("Model probability is high", "Escalate to a senior investigator; both the rule engine and the ML model independently flag this claim."),
]


def _actions_for(reasons: list[str]) -> list[str]:
    actions = []
    for reason in reasons:
        for keyword, action in ACTION_MAP:
            if keyword.lower() in reason.lower() and action not in actions:
                actions.append(action)
                break
    if not actions:
        actions.append("No specific risk factors identified; standard claim processing applies.")
    return actions


@dataclass
class WhyReport:
    claim_id: str
    spreadsheet_row: int | None
    policy_number: str
    final_status: str
    fraud_probability: float
    risk_score: float
    escalation_score: float
    confidence: str
    top_reasons: list[str]
    supporting_evidence: dict
    narrative_evidence: str
    contradictions: list[str]
    what_to_check: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            f"CLAIM ID: {self.claim_id}",
            f"SPREADSHEET ROW: {self.spreadsheet_row if self.spreadsheet_row is not None else 'N/A (new claim)'}",
            f"POLICY NUMBER: {self.policy_number}",
            f"FINAL STATUS: {self.final_status}",
            f"FRAUD PROBABILITY: {self.fraud_probability * 100:.1f}%",
            f"INVESTIGATION RISK SCORE: {self.risk_score:.1f}/100",
            f"ESCALATION SCORE: {self.escalation_score:.1f}/100",
            f"CONFIDENCE: {self.confidence}",
            "",
            "TOP REASONS FOR FLAGGING",
            *(f"  - {r}" for r in (self.top_reasons or ["No significant risk factors identified."])),
            "",
            "SUPPORTING EVIDENCE",
            *(f"  {k}: {v}" for k, v in self.supporting_evidence.items()),
            "",
            "NARRATIVE EVIDENCE",
            f"  {self.narrative_evidence or 'Not provided.'}",
            "",
            "CONTRADICTIONS",
            *(f"  - {c}" for c in (self.contradictions or ["None detected."])),
            "",
            "WHAT THE SENIOR INVESTIGATOR SHOULD CHECK",
            *(f"  - {a}" for a in self.what_to_check),
        ]
        return "\n".join(lines)


def build_why_report(
    *,
    claim_id: str,
    spreadsheet_row: int | None,
    policy_number,
    fusion_result,
    supporting_evidence: dict,
    narrative_evidence: str,
    contradictions: list[str],
) -> WhyReport:
    return WhyReport(
        claim_id=claim_id,
        spreadsheet_row=spreadsheet_row,
        policy_number=str(policy_number),
        final_status=fusion_result.final_tier,
        fraud_probability=fusion_result.fraud_probability,
        risk_score=fusion_result.risk_score,
        escalation_score=fusion_result.escalation_score,
        confidence=fusion_result.confidence,
        top_reasons=fusion_result.top_reasons,
        supporting_evidence=supporting_evidence,
        narrative_evidence=narrative_evidence,
        contradictions=contradictions,
        what_to_check=_actions_for(fusion_result.top_reasons),
    )
