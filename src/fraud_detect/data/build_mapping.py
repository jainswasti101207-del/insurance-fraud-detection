"""Build the single static lookup table joining CSV rows, narratives, and images.

Every other module reads claim_mapping.csv rather than re-deriving the
report-number <-> csv-row-index arithmetic or re-scanning the images folder.
"""
from __future__ import annotations

import pandas as pd

from fraud_detect.config import CLAIM_MAPPING_PATH, IMAGES_DIR
from fraud_detect.data.extract_narratives import extract_narratives
from fraud_detect.data.load_csv import load_claims


def build_mapping() -> pd.DataFrame:
    claims = load_claims()
    narratives = extract_narratives()

    image_by_number: dict[int, str] = {}
    for path in IMAGES_DIR.iterdir():
        if path.is_file() and path.stem.isdigit():
            image_by_number[int(path.stem)] = path.name

    rows = []
    for csv_row_index in range(len(claims)):
        narrative_rows = narratives[narratives["csv_row_index"] == csv_row_index]
        has_report = len(narrative_rows) > 0
        report_number = int(narrative_rows.iloc[0]["report_number"]) if has_report else None
        image_name = image_by_number.get(report_number) if report_number is not None else None

        rows.append(
            {
                "csv_row_index": csv_row_index,
                "policy_number": claims.iloc[csv_row_index]["PolicyNumber"],
                "report_number": report_number,
                "has_report": has_report,
                "has_image": image_name is not None,
                "image_path": f"Insurance_Fraud_Investigation_Images/{image_name}" if image_name else None,
            }
        )

    mapping = pd.DataFrame(rows)

    unmatched_images = set(image_by_number) - set(mapping["report_number"].dropna().astype(int))
    if unmatched_images:
        raise ValueError(f"Images with no matching CSV row: {sorted(unmatched_images)}")

    return mapping


def main() -> None:
    mapping = build_mapping()
    CLAIM_MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(CLAIM_MAPPING_PATH, index=False)
    print(f"Built mapping for {len(mapping)} claims -> {CLAIM_MAPPING_PATH}")
    print(f"  has_report: {mapping['has_report'].sum()}, has_image: {mapping['has_image'].sum()}")


if __name__ == "__main__":
    main()
