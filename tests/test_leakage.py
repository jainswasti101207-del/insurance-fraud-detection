from fraud_detect.data.load_csv import load_claims
from fraud_detect.features.leakage import assert_no_leakage, get_feature_columns


def test_feature_columns_exclude_leakage_and_identifiers():
    df = load_claims()
    cols = get_feature_columns(df)
    assert "FraudFound_P" not in cols
    assert "curation_category" not in cols
    assert "PolicyNumber" not in cols
    assert "RepNumber" not in cols
    assert "Make" not in cols
    assert_no_leakage(cols)


def test_assert_no_leakage_raises_on_label_column():
    try:
        assert_no_leakage(["FraudFound_P", "Age"])
    except ValueError:
        return
    raise AssertionError("assert_no_leakage should have raised")
