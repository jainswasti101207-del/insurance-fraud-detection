"""Parse Accident_Reports.docx into one narrative record per claim.

The document is a flat sequence of paragraphs in groups of 3: an "Incident
Overview" paragraph (which carries the leading "N." report number and, for
two fraud cases, an alternate "N. ACCIDENT INVESTIGATION REPORT" heading), a
"Claim Evaluation & Risk Assessment" paragraph, and a blank separator. We
concatenate the first two paragraphs of each group into one narrative_text.
"""
from __future__ import annotations

import re

import docx
import pandas as pd

from fraud_detect.config import NARRATIVES_PATH, REPORTS_DOCX_PATH, REPORT_NUMBER_OFFSET

REPORT_NUMBER_RE = re.compile(r"^(\d+)\.\s*")
ALT_HEADING = "ACCIDENT INVESTIGATION REPORT"


def extract_narratives() -> pd.DataFrame:
    document = docx.Document(str(REPORTS_DOCX_PATH))
    paragraphs = [p.text for p in document.paragraphs]

    records = []
    i = 0
    while i < len(paragraphs):
        text = paragraphs[i].strip()
        if not text:
            i += 1
            continue
        match = REPORT_NUMBER_RE.match(text)
        if not match:
            raise ValueError(f"Expected paragraph {i} to start with a report number, got: {text[:80]!r}")
        report_number = int(match.group(1))

        overview_para = text
        has_alt_heading = ALT_HEADING in overview_para
        if has_alt_heading:
            overview_para = overview_para.replace(f"{report_number}. {ALT_HEADING} ", "").strip()
        else:
            overview_para = REPORT_NUMBER_RE.sub("", overview_para).strip()

        eval_para = paragraphs[i + 1].strip() if i + 1 < len(paragraphs) else ""
        narrative_text = f"{overview_para} {eval_para}".strip()

        records.append(
            {
                "report_number": report_number,
                "csv_row_index": report_number - REPORT_NUMBER_OFFSET,
                "narrative_text": narrative_text,
                "has_alt_fraud_heading": has_alt_heading,
            }
        )
        i += 2
        # skip the blank separator paragraph if present
        if i < len(paragraphs) and not paragraphs[i].strip():
            i += 1

    df = pd.DataFrame(records).sort_values("report_number").reset_index(drop=True)
    return df


def main() -> None:
    df = extract_narratives()
    NARRATIVES_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(NARRATIVES_PATH, index=False)
    print(f"Extracted {len(df)} narratives -> {NARRATIVES_PATH}")


if __name__ == "__main__":
    main()
