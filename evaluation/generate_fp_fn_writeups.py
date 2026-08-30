"""Instructions_Set_Reports.docx §24: for every false positive/negative,
explain why the system got it wrong. Uses the honest out-of-fold probability
(not the deployed model's in-sample prediction) to identify FP/FN, consistent
with run_full_evaluation.py's metrics.
"""
from __future__ import annotations

import pandas as pd

from fraud_detect.config import CSV_PATH, EVALUATION_DIR
from fraud_detect.data.extract_narratives import extract_narratives

THRESHOLD = 0.5


def main() -> None:
    per_claim = pd.read_csv(EVALUATION_DIR / "per_claim_predictions.csv")
    claims = pd.read_csv(CSV_PATH)
    narratives = extract_narratives().set_index("csv_row_index")

    per_claim["oof_predicted_fraud"] = (per_claim["oof_probability"] >= THRESHOLD).astype(int)
    false_positives = per_claim[(per_claim["oof_predicted_fraud"] == 1) & (per_claim["actual_fraud"] == 0)]
    false_negatives = per_claim[(per_claim["oof_predicted_fraud"] == 0) & (per_claim["actual_fraud"] == 1)]

    lines = ["# False Positive / False Negative Analysis\n"]
    lines.append(
        f"Out-of-fold, at threshold {THRESHOLD}: {len(false_positives)} false positives, "
        f"{len(false_negatives)} false negatives (see docs/limitations.md for small-sample caveats).\n"
    )

    lines.append("\n## False Positives (legitimate claims flagged as likely fraud)\n")
    if false_positives.empty:
        lines.append("None.\n")
    for _, r in false_positives.iterrows():
        row = claims.loc[r["csv_row_index"]]
        narrative = narratives.loc[r["csv_row_index"], "narrative_text"] if r["csv_row_index"] in narratives.index else ""
        lines.append(f"\n### Claim row {int(r['csv_row_index'])} (policy {r['policy_number']})\n")
        lines.append(f"- OOF fraud probability: {r['oof_probability']:.3f}, rule score: {r['rule_score']}, actual: legitimate ({row['curation_category']})\n")
        lines.append(
            f"- Why the system thought this was suspicious: PastNumberOfClaims={row['PastNumberOfClaims']}, "
            f"PoliceReportFiled={row['PoliceReportFiled']}, WitnessPresent={row['WitnessPresent']}, "
            f"Fault={row['Fault']}, severity_bucket={row['severity_bucket']}, make_fraud_rate={row['make_fraud_rate']:.3f}.\n"
        )
        lines.append(f"- Narrative excerpt: {narrative[:300]}...\n")

    lines.append("\n## False Negatives (fraud claims the system missed)\n")
    if false_negatives.empty:
        lines.append("None.\n")
    for _, r in false_negatives.iterrows():
        row = claims.loc[r["csv_row_index"]]
        narrative = narratives.loc[r["csv_row_index"], "narrative_text"] if r["csv_row_index"] in narratives.index else ""
        lines.append(f"\n### Claim row {int(r['csv_row_index'])} (policy {r['policy_number']})\n")
        lines.append(f"- OOF fraud probability: {r['oof_probability']:.3f}, rule score: {r['rule_score']}, actual: fraud\n")
        lines.append(
            f"- Why the system missed it: PastNumberOfClaims={row['PastNumberOfClaims']}, "
            f"PoliceReportFiled={row['PoliceReportFiled']}, WitnessPresent={row['WitnessPresent']}, "
            f"Fault={row['Fault']}, severity_bucket={row['severity_bucket']}, make_fraud_rate={row['make_fraud_rate']:.3f}. "
            f"Note the system's rule-based escalation logic (mandatory triggers) may still have caught this "
            f"claim (see final_tier={r['final_tier']}) even where the ML model's cross-validated probability alone did not.\n"
        )
        lines.append(f"- Narrative excerpt: {narrative[:300]}...\n")

    out_path = EVALUATION_DIR / "fp_fn_analysis.md"
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(false_positives)} FP, {len(false_negatives)} FN)")


if __name__ == "__main__":
    main()
