from fraud_detect.rules.scoring import total_risk_score


def _score(**overrides):
    base = dict(
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
    base.update(overrides)
    return total_risk_score(**base)


def test_clean_claim_scores_low():
    result = _score()
    assert result.risk_score_0_100 < 15


def test_known_fraud_row_scores_high():
    # Mirrors CSV row 14 / report 16: Accura, no police report, no witness,
    # more than 4 past claims, policyholder fault, extensive repairs.
    result = _score(
        police_report_filed="No",
        witness_present="No",
        past_number_of_claims="more than 4",
        delay_days=5,
        fault="Policy Holder",
        severity_bucket="Low",
        number_of_suppliments="more than 5",
        make_fraud_rate=0.125,
        dataset_mean_make_fraud_rate=0.05,
    )
    assert result.risk_score_0_100 > 60


def test_evidence_score_caps_at_max():
    result = _score(police_report_filed="No", witness_present="No")
    evidence = next(s for s in result.sub_scores if s.name == "Evidence Risk")
    assert evidence.points <= evidence.max_points


def test_reporting_behavior_falls_back_to_flag_when_delay_unknown():
    result = _score(delay_days=None, filing_delay_flag=1)
    reporting = next(s for s in result.sub_scores if s.name == "Reporting Behavior")
    assert reporting.points > 0
