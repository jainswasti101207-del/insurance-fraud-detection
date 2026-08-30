"""Instructions_Set_Reports.docx §27: run every claim through the system
WITHOUT touching FraudFound_P/curation_category as inputs, then join ground
truth back on for scoring only. Runs with use_llm=False - Gemini's narrative/
image prose doesn't factor into the numeric rule score, ML probability, or
tier decision (see pipeline.py/decision/fusion.py), so leaving it out here
keeps this evaluation fast, deterministic, and reproducible without API calls.

IMPORTANT: the deployed model (models/model.joblib) is refit on all 100 rows,
so calling it on those same 100 rows (via pipeline.run_pipeline) gives
in-sample predictions that look artificially perfect - that is expected
deployed-model behavior on its own training data, not a meaningful measure of
generalization. The "Model Performance" metrics below are therefore computed
from ml/train.py's out-of-fold cross-validation probabilities
(evaluation_report/oof_predictions.csv), which is the honest estimate of how
the model performs on claims it wasn't fit on. Both numbers are kept in
per_claim_predictions.csv for transparency, clearly labeled.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import confusion_matrix

from fraud_detect.config import CSV_PATH, EVALUATION_DIR
from fraud_detect.data.build_mapping import build_mapping
from fraud_detect.data.extract_narratives import extract_narratives
from fraud_detect.ml.evaluate import compute_metrics
from fraud_detect.pipeline import ClaimInput, run_pipeline


def run_all_claims() -> pd.DataFrame:
    claims = pd.read_csv(CSV_PATH)
    narratives = extract_narratives().set_index("csv_row_index")
    mapping = build_mapping().set_index("csv_row_index")

    rows = []
    for i in range(len(claims)):
        row = claims.iloc[i]
        claim = ClaimInput(
            claim_id=f"CLM-{i}",
            policy_number=row["PolicyNumber"],
            raw_fields=row.to_dict(),
            spreadsheet_row=i,
            narrative_text=narratives.loc[i, "narrative_text"],
            engineered_fields=row.to_dict(),
        )
        result = run_pipeline(claim, use_llm=False)
        rows.append(
            {
                "csv_row_index": i,
                "policy_number": row["PolicyNumber"],
                "rule_score": result.why_report.risk_score,
                "ml_probability_deployed": result.why_report.fraud_probability,
                "escalation_score": result.why_report.escalation_score,
                "final_tier": result.why_report.final_status,
                "escalated": result.why_report.final_status in ("ESCALATE", "HIGH_FRAUD_RISK"),
                "actual_fraud": int(row["FraudFound_P"]),
                "actual_curation_category": row["curation_category"],
            }
        )
    df = pd.DataFrame(rows)

    oof = pd.read_csv(EVALUATION_DIR / "oof_predictions.csv")
    df = df.merge(oof[["csv_row_index", "oof_probability"]], on="csv_row_index", how="left")
    return df


def main() -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    df = run_all_claims()
    df.to_csv(EVALUATION_DIR / "per_claim_predictions.csv", index=False)

    y_true = df["actual_fraud"].values
    y_prob = df["oof_probability"].values  # honest, out-of-fold - see module docstring
    metrics = compute_metrics(y_true, y_prob, threshold=0.5)

    metrics_dict = {
        "n_claims": len(df),
        "n_positive": int(y_true.sum()),
        "probability_source": "out-of-fold cross-validation (ml/train.py) - NOT the deployed "
        "model's in-sample predictions, which would be artificially inflated on its own training data.",
        "small_sample_caveat": (
            "100 rows / 11 fraud-labeled claims is too small for statistically reliable metrics. "
            "These numbers describe performance on this curated sample only; see docs/limitations.md."
        ),
        "accuracy": round(metrics.accuracy, 3),
        "precision": round(metrics.precision, 3),
        "recall": round(metrics.recall, 3),
        "f1": round(metrics.f1, 3),
        "roc_auc": round(metrics.roc_auc, 3) if metrics.roc_auc == metrics.roc_auc else None,
        "pr_auc": round(metrics.pr_auc, 3) if metrics.pr_auc == metrics.pr_auc else None,
        "confusion_matrix": metrics.confusion,
        "false_positive_rate": round(metrics.false_positive_rate, 3),
        "n_actual_fraud": metrics.n_actual_fraud,
        "n_detected": metrics.n_detected,
        "n_missed": metrics.n_missed,
        "n_false_positives": metrics.n_false_positives,
    }
    with open(EVALUATION_DIR / "metrics.json", "w") as f:
        json.dump(metrics_dict, f, indent=2)

    # Escalation performance (§23): among actual fraud, how many escalated;
    # among legitimate, how many were escalated unnecessarily.
    actual_fraud_mask = df["actual_fraud"] == 1
    escalation_perf = {
        "pct_actual_fraud_escalated": round(df.loc[actual_fraud_mask, "escalated"].mean() * 100, 1),
        "pct_legitimate_escalated": round(df.loc[~actual_fraud_mask, "escalated"].mean() * 100, 1),
        "escalation_precision": round(
            (df["escalated"] & actual_fraud_mask).sum() / max(df["escalated"].sum(), 1), 3
        ),
        "escalation_recall": round(
            (df["escalated"] & actual_fraud_mask).sum() / max(actual_fraud_mask.sum(), 1), 3
        ),
        "tier_distribution": df["final_tier"].value_counts().to_dict(),
    }
    with open(EVALUATION_DIR / "escalation_performance.md", "w") as f:
        f.write("# Escalation Performance\n\n")
        f.write(
            "> Escalation decisions here come from the full pipeline (rule engine + escalation "
            "logic + the deployed model's in-sample ML probability). The rule engine and escalation "
            "logic are not fit to data, so they don't have an in-sample/out-of-sample distinction; "
            "only the ML probability component does (see metrics.md for the honest, out-of-fold "
            "model-only metrics).\n\n"
        )
        f.write(f"- % of actual fraud cases escalated: {escalation_perf['pct_actual_fraud_escalated']}%\n")
        f.write(f"- % of legitimate cases escalated: {escalation_perf['pct_legitimate_escalated']}%\n")
        f.write(f"- Escalation precision: {escalation_perf['escalation_precision']}\n")
        f.write(f"- Escalation recall: {escalation_perf['escalation_recall']}\n\n")
        f.write("## Tier distribution\n\n")
        for tier, count in escalation_perf["tier_distribution"].items():
            f.write(f"- {tier}: {count}\n")

    cm = confusion_matrix(y_true, (y_prob >= 0.5).astype(int), labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(cm, cmap="Blues")
    for (i, j), val in __import__("numpy").ndenumerate(cm):
        ax.text(j, i, str(val), ha="center", va="center", fontsize=14)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Legitimate", "Fraud"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Legitimate", "Fraud"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix (out-of-fold, threshold=0.5)")
    fig.tight_layout()
    fig.savefig(EVALUATION_DIR / "confusion_matrix.png", dpi=150)

    with open(EVALUATION_DIR / "metrics.md", "w") as f:
        f.write("# ML Model Performance (out-of-fold cross-validation)\n\n")
        f.write(f"n={metrics_dict['n_claims']} claims, {metrics_dict['n_positive']} fraud-labeled.\n\n")
        f.write(f"> {metrics_dict['probability_source']}\n\n")
        f.write(f"> {metrics_dict['small_sample_caveat']}\n\n")
        for k in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate"]:
            f.write(f"- {k}: {metrics_dict[k]}\n")
        f.write(f"\nConfusion matrix (rows=actual, cols=predicted): {metrics_dict['confusion_matrix']}\n")
        f.write(f"\nFraud detection: {metrics_dict['n_detected']}/{metrics_dict['n_actual_fraud']} detected, "
                f"{metrics_dict['n_missed']} missed, {metrics_dict['n_false_positives']} false positives.\n")

    print("Evaluation complete.")
    print(json.dumps(metrics_dict, indent=2))
    print(json.dumps(escalation_perf, indent=2))


if __name__ == "__main__":
    main()
