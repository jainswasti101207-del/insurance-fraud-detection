"""Threshold sweep and 4-tier cut-point selection (Instructions_Set_Reports.docx §14)."""
from __future__ import annotations

import numpy as np

from fraud_detect.ml.evaluate import compute_metrics

SWEEP_THRESHOLDS = np.round(np.arange(0.1, 0.95, 0.05), 2)


def sweep(y_true: np.ndarray, y_prob: np.ndarray) -> list[dict]:
    rows = []
    for t in SWEEP_THRESHOLDS:
        m = compute_metrics(y_true, y_prob, threshold=t)
        rows.append(
            {
                "threshold": float(t),
                "precision": round(m.precision, 3),
                "recall": round(m.recall, 3),
                "f1": round(m.f1, 3),
                "false_positive_rate": round(m.false_positive_rate, 3),
            }
        )
    return rows


def recommend_tier_thresholds(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Proposes probability cut-points for the 4 decision tiers.

    This is a business decision (relative cost of missed fraud vs wasted
    investigation time), not a purely statistical one. Given a tiny, imbalanced
    dataset (100 rows, 11 positives), we bias toward recall: prefer catching
    more fraud at the cost of more MONITOR/ESCALATE false positives, since the
    instructions explicitly frame those as lower-cost than missed fraud, while
    still requiring a real recall improvement to justify each higher tier.
    """
    rows = sweep(y_true, y_prob)
    # Pick the lowest threshold achieving recall >= 0.8 as the ESCALATE cut,
    # and the highest threshold still achieving recall >= 0.5 as HIGH_FRAUD_RISK.
    escalate_candidates = [r for r in rows if r["recall"] >= 0.8]
    high_risk_candidates = [r for r in rows if r["recall"] >= 0.5]

    escalate_threshold = min((r["threshold"] for r in escalate_candidates), default=0.3)
    high_risk_threshold = max((r["threshold"] for r in high_risk_candidates), default=0.6)
    if high_risk_threshold <= escalate_threshold:
        high_risk_threshold = min(escalate_threshold + 0.2, 0.9)
    monitor_threshold = max(escalate_threshold - 0.15, 0.05)

    return {
        "legitimate_below": round(monitor_threshold, 2),
        "monitor_below": round(escalate_threshold, 2),
        "escalate_below": round(high_risk_threshold, 2),
        # >= escalate_below is HIGH_FRAUD_RISK
        "sweep": rows,
    }
