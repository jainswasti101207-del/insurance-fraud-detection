from datetime import date

import pandas as pd

from fraud_detect.pipeline import ClaimInput, run_pipeline


def test_historical_claim_replay_without_llm():
    claims = pd.read_csv("data/raw/curated_100_claims_with_ground_truth.csv")
    narratives = pd.read_csv("data/processed/narratives_extracted.csv").set_index("csv_row_index")
    row = claims.loc[14]
    claim = ClaimInput(
        claim_id="CLM-14",
        policy_number=row["PolicyNumber"],
        raw_fields=row.to_dict(),
        spreadsheet_row=14,
        narrative_text=narratives.loc[14, "narrative_text"],
        engineered_fields=row.to_dict(),
    )
    result = run_pipeline(claim, use_llm=False)
    assert result.why_report.final_status in ("LEGITIMATE", "MONITOR", "ESCALATE", "HIGH_FRAUD_RISK")
    assert result.llm_available is False
    assert 0.0 <= result.why_report.fraud_probability <= 1.0


def test_brand_new_claim_with_no_narrative_or_image():
    raw = dict(
        Make="Toyota", Sex="Female", MaritalStatus="Married", Age=45,
        Fault="Third Party", PolicyType="Sedan - Collision", VehicleCategory="Sedan",
        VehiclePrice="20000 to 29000", Deductible=400, DriverRating=2,
        Days_Policy_Accident="more than 30", Days_Policy_Claim="more than 30",
        PastNumberOfClaims="none", AgeOfVehicle="5 years", AgeOfPolicyHolder="41 to 50",
        PoliceReportFiled="Yes", WitnessPresent="Yes", AgentType="External",
        NumberOfSuppliments="none", AddressChange_Claim="no change", NumberOfCars="1 vehicle",
        Year=2024, BasePolicy="Collision", AccidentArea="Urban",
    )
    claim = ClaimInput(
        claim_id="NEW-001",
        policy_number="TEST-001",
        raw_fields=raw,
        accident_date=date(2026, 1, 10),
        claim_date=date(2026, 1, 12),
    )
    result = run_pipeline(claim, use_llm=False)
    assert result.why_report.final_status == "LEGITIMATE"
    assert result.contradictions == []
    assert result.narrative_analysis is None
    assert result.image_analysis is None


def test_suspicious_brand_new_claim_triggers_high_fraud_risk():
    raw = dict(
        Make="Toyota", Sex="Female", MaritalStatus="Married", Age=45,
        Fault="Policy Holder", PolicyType="Sedan - All Perils", VehicleCategory="Sedan",
        VehiclePrice="more than 69000", Deductible=400, DriverRating=2,
        Days_Policy_Accident="more than 30", Days_Policy_Claim="more than 30",
        PastNumberOfClaims="more than 4", AgeOfVehicle="5 years", AgeOfPolicyHolder="41 to 50",
        PoliceReportFiled="No", WitnessPresent="No", AgentType="External",
        NumberOfSuppliments="more than 5", AddressChange_Claim="no change", NumberOfCars="1 vehicle",
        Year=2024, BasePolicy="All Perils", AccidentArea="Urban",
    )
    claim = ClaimInput(
        claim_id="NEW-002",
        policy_number="TEST-002",
        raw_fields=raw,
        accident_date=date(2026, 1, 1),
        claim_date=date(2026, 1, 20),
    )
    result = run_pipeline(claim, use_llm=False)
    assert result.why_report.final_status == "HIGH_FRAUD_RISK"
    assert result.why_report.fraud_probability > 0.8
