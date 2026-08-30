from fraud_detect.rules.escalation import evaluate_escalation
from fraud_detect.rules.scoring import total_risk_score


def test_no_single_factor_alone_triggers_mandatory_escalation():
    """§15: never escalate solely on high value, high severity, or missing
    police report alone."""
    risk = total_risk_score(
        police_report_filed="No",
        witness_present="Yes",
        past_number_of_claims="none",
        delay_days=1,
        filing_delay_flag=0,
        fault="Third Party",
        severity_bucket="Low",
        high_value_vehicle_flag=1,
        number_of_suppliments="none",
        make_fraud_rate=0.05,
        dataset_mean_make_fraud_rate=0.05,
    )
    result = evaluate_escalation(
        police_report_filed="No",
        witness_present="Yes",
        past_number_of_claims="none",
        fault="Third Party",
        high_value_vehicle_flag=1,
        severity_bucket="Low",
        number_of_suppliments="none",
        make_fraud_rate=0.05,
        dataset_mean_make_fraud_rate=0.05,
        delay_days=1,
        filing_delay_flag=0,
        risk_result=risk,
        ml_probability=0.1,
        ml_high_probability_threshold=0.7,
        contradiction_count=0,
    )
    assert result.mandatory_triggered is False


def test_no_evidence_plus_repeat_offender_plus_delay_triggers_mandatory():
    risk = total_risk_score(
        police_report_filed="No",
        witness_present="No",
        past_number_of_claims="more than 4",
        delay_days=10,
        filing_delay_flag=1,
        fault="Policy Holder",
        severity_bucket="Low",
        high_value_vehicle_flag=0,
        number_of_suppliments="more than 5",
        make_fraud_rate=0.125,
        dataset_mean_make_fraud_rate=0.05,
    )
    result = evaluate_escalation(
        police_report_filed="No",
        witness_present="No",
        past_number_of_claims="more than 4",
        fault="Policy Holder",
        high_value_vehicle_flag=0,
        severity_bucket="Low",
        number_of_suppliments="more than 5",
        make_fraud_rate=0.125,
        dataset_mean_make_fraud_rate=0.05,
        delay_days=10,
        filing_delay_flag=1,
        risk_result=risk,
        ml_probability=0.6,
        ml_high_probability_threshold=0.7,
        contradiction_count=0,
    )
    assert result.mandatory_triggered is True


def test_contradiction_forces_escalation():
    risk = total_risk_score(
        police_report_filed="Yes",
        witness_present="Yes",
        past_number_of_claims="none",
        delay_days=1,
        filing_delay_flag=0,
        fault="Third Party",
        severity_bucket="Low",
        high_value_vehicle_flag=0,
        number_of_suppliments="none",
        make_fraud_rate=0.05,
        dataset_mean_make_fraud_rate=0.05,
    )
    result = evaluate_escalation(
        police_report_filed="Yes",
        witness_present="Yes",
        past_number_of_claims="none",
        fault="Third Party",
        high_value_vehicle_flag=0,
        severity_bucket="Low",
        number_of_suppliments="none",
        make_fraud_rate=0.05,
        dataset_mean_make_fraud_rate=0.05,
        delay_days=1,
        filing_delay_flag=0,
        risk_result=risk,
        ml_probability=0.1,
        ml_high_probability_threshold=0.7,
        contradiction_count=1,
    )
    assert result.mandatory_triggered is True
