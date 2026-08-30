"""Point values for the rule-based risk score (Instructions_Set_Reports.docx §10).

Every constant below is cited to its source section so the scoring logic in
scoring.py never contains a bare magic number.
"""
from __future__ import annotations

# --- Evidence Risk (0-25) --- §10
POLICE_ABSENT_POINTS = 10
WITNESS_ABSENT_POINTS = 10
BOTH_ABSENT_BONUS_POINTS = 5
EVIDENCE_RISK_CAP = 25

# --- Claim History (0-15) --- §10
# Maps the CSV's categorical PastNumberOfClaims values directly (avoids
# re-deriving from past_claims_numeric and risking an off-by-one mismatch).
PAST_CLAIMS_POINTS = {
    "none": 0,
    "1": 2,
    "2 to 4": 8,
    "more than 4": 15,
}
CLAIM_HISTORY_CAP = 15

# --- Reporting Behavior (0-15) --- §10, indicator 4
# Thresholds apply to an exact accident->claim delay in days when available
# (narrative-derived for historical claims, user-entered for new claims).
DELAY_LOW_MAX_DAYS = 2
DELAY_MODERATE_MAX_DAYS = 7
DELAY_LOW_POINTS = 0
DELAY_MODERATE_POINTS = 5
DELAY_HIGH_POINTS = 15
# Fallback when an exact delay isn't determinable: use the CSV's categorical
# filing_delay_flag as a coarse proxy (documented dataset limitation - see
# docs/limitations.md - this flag is constant across the curated 100-row
# sample, so it only adds real discriminative power for new claims where
# exact dates are always collected).
DELAY_FLAG_FALLBACK_POINTS = 5

# --- Fault (0-10) --- §10
POLICYHOLDER_FAULT_POINTS = 10
THIRD_PARTY_FAULT_POINTS = 0

# --- Financial Exposure (0-15) --- §10 (exact formula left to implementer)
FINANCIAL_EXPOSURE_CAP = 15

# --- Vehicle / Claim Pattern (0-10) --- §10 (exact formula left to implementer)
VEHICLE_PATTERN_CAP = 10

# --- Statistical Risk (0-5) --- §10
STATISTICAL_RISK_CAP = 5

# Section 10's stated per-category maximums sum to 95 (25+15+15+10+15+10+5),
# not 100. We rescale the raw total to a 0-100 risk score in one documented
# step rather than distorting individual sub-scores to force a false 100.
RAW_SCORE_MAX = (
    EVIDENCE_RISK_CAP
    + CLAIM_HISTORY_CAP
    + DELAY_HIGH_POINTS
    + POLICYHOLDER_FAULT_POINTS
    + FINANCIAL_EXPOSURE_CAP
    + VEHICLE_PATTERN_CAP
    + STATISTICAL_RISK_CAP
)
