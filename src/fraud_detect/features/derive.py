"""Derives the CSV's engineered columns from raw claim fields, for brand-new
claims entered through the app (which only supply raw fields, not the
pre-engineered ones baked into curated_100_claims_with_ground_truth.csv).

Mappings below were reverse-engineered by cross-referencing the curated CSV's
raw and engineered columns directly (see docs/data_documentation.md) and are
exact matches where verified against real rows (vehicle_price_midpoint,
coverage_multiplier, severity_proxy, vehicle_age_numeric,
policyholder_age_numeric, past_claims_numeric, address_change_numeric,
month_numeric, weekday_numeric). suspicion_score's original formula could not
be fully reverse-engineered from the 100-row sample (it depends on more than
the fields we could isolate), so new claims use a simple, documented,
transparent approximation instead - see suspicion_score() below - while the
100 historical claims always use their original CSV value directly.
"""
from __future__ import annotations

from datetime import date

from fraud_detect.features.engineer import get_dataset_mean_make_fraud_rate

VEHICLE_PRICE_MIDPOINT = {
    "less than 20000": 15000,
    "20000 to 29000": 24500,
    "30000 to 39000": 34500,
    "40000 to 59000": 49500,
    "60000 to 69000": 64500,
    "more than 69000": 80000,
}
HIGH_VALUE_THRESHOLD = 65000

COVERAGE_MULTIPLIER = {"Liability": 0.4, "Collision": 0.7, "All Perils": 1.0}

VEHICLE_AGE_NUMERIC = {"new": 0, "2 years": 2, "3 years": 3, "4 years": 4, "5 years": 5, "6 years": 6, "7 years": 7, "more than 7": 8}

POLICYHOLDER_AGE_ORDER = [
    "16 to 17", "18 to 20", "21 to 25", "26 to 30", "31 to 35",
    "36 to 40", "41 to 50", "51 to 65", "over 65",
]

ADDRESS_CHANGE_NUMERIC = {"no change": 0, "over 8 years": 0, "4 to 8 years": 1, "2 to 3 years": 2, "1 year": 3}

PAST_CLAIMS_NUMERIC = {"none": 0, "1": 1, "2 to 4": 2, "more than 4": 3}

DAYS_POLICY_NUMERIC = {"none": 0, "1 to 7": 1, "8 to 15": 2, "15 to 30": 3, "more than 30": 4}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def date_to_fields(d: date) -> dict:
    """Derives Month/DayOfWeek/WeekOfMonth from an actual date, so the New
    Claim form only needs a date-picker rather than separate dropdowns that
    could disagree with each other."""
    return {
        "Month": MONTHS[d.month - 1],
        "DayOfWeek": WEEKDAYS[d.weekday()],
        "WeekOfMonth": (d.day - 1) // 7 + 1,
    }


def severity_bucket(severity_proxy: float) -> str:
    if severity_proxy <= 16000:
        return "Low"
    if severity_proxy <= 30000:
        return "Medium"
    return "High"


def suspicion_score(no_evidence_flag: int, repeat_offender_flag: int, filing_delay_flag: int) -> int:
    """Simple, documented approximation for new claims (see module docstring):
    one point each for no independent evidence and for repeat-offender
    history; historical claims never use this, they replay their real CSV
    suspicion_score instead."""
    return min(2, int(no_evidence_flag) + int(repeat_offender_flag) + (1 if filing_delay_flag and no_evidence_flag else 0))


def derive_engineered_fields(raw: dict, delay_days: int | None, make_fraud_rate_table: dict | None = None) -> dict:
    vehicle_price_midpoint = VEHICLE_PRICE_MIDPOINT.get(raw["VehiclePrice"], 24500)
    coverage_multiplier = COVERAGE_MULTIPLIER.get(raw["BasePolicy"], 0.7)
    severity_proxy = vehicle_price_midpoint * coverage_multiplier

    police_yes = str(raw.get("PoliceReportFiled")).strip() == "Yes"
    witness_yes = str(raw.get("WitnessPresent")).strip() == "Yes"
    no_evidence_flag = int(not police_yes and not witness_yes)
    evidence_score = int(police_yes) + int(witness_yes)

    past_claims_key = str(raw.get("PastNumberOfClaims", "none")).strip()
    repeat_offender_flag = int(past_claims_key == "more than 4")

    filing_delay_flag = int(delay_days is not None and delay_days > 7)
    quick_claim_flag = int(delay_days is not None and delay_days <= 2)

    address_change_key = str(raw.get("AddressChange_Claim", "no change")).strip()
    recent_address_change_flag = int(address_change_key != "no change")

    age = int(raw.get("Age", 30))
    young_driver_flag = int(age < 21)

    make = raw.get("Make")
    make_rate = (make_fraud_rate_table or {}).get(make, get_dataset_mean_make_fraud_rate())

    fields = {
        "vehicle_price_midpoint": vehicle_price_midpoint,
        "coverage_multiplier": coverage_multiplier,
        "severity_proxy": severity_proxy,
        "severity_bucket": severity_bucket(severity_proxy),
        "days_policy_accident_numeric": DAYS_POLICY_NUMERIC.get(raw.get("Days_Policy_Accident"), 4),
        "days_policy_claim_numeric": DAYS_POLICY_NUMERIC.get(raw.get("Days_Policy_Claim"), 4),
        "quick_claim_flag": quick_claim_flag,
        "filing_delay_flag": filing_delay_flag,
        "past_claims_numeric": PAST_CLAIMS_NUMERIC.get(past_claims_key, 0),
        "repeat_offender_flag": repeat_offender_flag,
        "address_change_numeric": ADDRESS_CHANGE_NUMERIC.get(address_change_key, 0),
        "recent_address_change_flag": recent_address_change_flag,
        "no_evidence_flag": no_evidence_flag,
        "evidence_score": evidence_score,
        "vehicle_age_numeric": VEHICLE_AGE_NUMERIC.get(raw.get("AgeOfVehicle"), 4),
        "high_value_vehicle_flag": int(vehicle_price_midpoint >= HIGH_VALUE_THRESHOLD),
        "policyholder_age_numeric": POLICYHOLDER_AGE_ORDER.index(raw["AgeOfPolicyHolder"]) if raw.get("AgeOfPolicyHolder") in POLICYHOLDER_AGE_ORDER else 4,
        "young_driver_flag": young_driver_flag,
        "fault_x_basepolicy": f"{raw.get('Fault')}_{raw.get('BasePolicy')}",
        "make_fraud_rate": make_rate,
        "month_numeric": MONTHS.index(raw["Month"]) + 1 if raw.get("Month") in MONTHS else 6,
        "weekday_numeric": WEEKDAYS.index(raw["DayOfWeek"]) if raw.get("DayOfWeek") in WEEKDAYS else 3,
    }
    fields["suspicion_score"] = suspicion_score(no_evidence_flag, repeat_offender_flag, filing_delay_flag)
    return fields
