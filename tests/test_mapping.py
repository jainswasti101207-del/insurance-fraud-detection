from fraud_detect.data.build_mapping import build_mapping
from fraud_detect.data.load_csv import load_claims


def test_all_claims_mapped_to_a_narrative():
    mapping = build_mapping()
    assert len(mapping) == 100
    assert mapping["has_report"].sum() == 100


def test_image_count_matches_disk():
    mapping = build_mapping()
    assert mapping["has_image"].sum() == 26


def test_report_16_maps_to_csv_row_14():
    mapping = build_mapping()
    claims = load_claims()
    row = mapping[mapping["csv_row_index"] == 14].iloc[0]
    assert row["report_number"] == 16
    assert claims.loc[14, "Make"] == "Accura"
    assert claims.loc[14, "FraudFound_P"] == 1
    assert row["has_image"]
