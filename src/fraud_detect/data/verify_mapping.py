"""Milestone-1 gate: hard assertions on the data layer before anything else trusts it."""
from __future__ import annotations

from fraud_detect.config import IMAGES_DIR
from fraud_detect.data.build_mapping import build_mapping
from fraud_detect.data.load_csv import load_claims


def verify() -> None:
    claims = load_claims()
    mapping = build_mapping()

    assert len(mapping) == len(claims) == 100, f"Expected 100 claims, got {len(claims)}/{len(mapping)}"

    n_reports = mapping["has_report"].sum()
    assert n_reports == 100, f"Expected all 100 claims to have a narrative, got {n_reports}"

    n_images = mapping["has_image"].sum()
    n_image_files = sum(1 for p in IMAGES_DIR.iterdir() if p.is_file())
    assert n_images == n_image_files, (
        f"Expected every image file to map to a claim: {n_images} mapped vs {n_image_files} files on disk"
    )

    # Spot check: report 16 -> csv row 14 -> Accura, 79yo, urban, policyholder fault, fraud.
    row14 = mapping[mapping["csv_row_index"] == 14].iloc[0]
    assert row14["report_number"] == 16, f"Expected report 16 for csv row 14, got {row14['report_number']}"
    csv_row14 = claims.loc[14]
    assert csv_row14["Make"] == "Accura", f"Expected Make=Accura for csv row 14, got {csv_row14['Make']}"
    assert csv_row14["Age"] == 79, f"Expected Age=79 for csv row 14, got {csv_row14['Age']}"
    assert csv_row14["FraudFound_P"] == 1, "Expected csv row 14 to be a ground-truth fraud case"
    assert row14["has_image"], "Expected csv row 14 (report 16) to have an image (16.png)"

    print("verify_mapping: PASSED")
    print(f"  100/100 claims mapped, {n_reports}/100 narratives, {n_images}/{n_image_files} images")
    print("  report-16 <-> csv-row-14 spot check OK (Accura, age 79, FraudFound_P=1, has image)")


if __name__ == "__main__":
    verify()
