"""Reusable metric computation (Instructions_Set_Reports.docx §12/§13/§23)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class Metrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    confusion: list[list[int]]
    false_positive_rate: float
    n_actual_fraud: int
    n_detected: int
    n_missed: int
    n_false_positives: int


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Metrics:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # ROC-AUC/PR-AUC are undefined with only one class present; guard for
    # small-sample edge cases (e.g. a single CV fold with zero positives).
    try:
        roc = roc_auc_score(y_true, y_prob)
    except ValueError:
        roc = float("nan")
    try:
        pr_auc = average_precision_score(y_true, y_prob)
    except ValueError:
        pr_auc = float("nan")

    return Metrics(
        accuracy=accuracy_score(y_true, y_pred),
        precision=precision_score(y_true, y_pred, zero_division=0),
        recall=recall_score(y_true, y_pred, zero_division=0),
        f1=f1_score(y_true, y_pred, zero_division=0),
        roc_auc=roc,
        pr_auc=pr_auc,
        confusion=[[int(tn), int(fp)], [int(fn), int(tp)]],
        false_positive_rate=fpr,
        n_actual_fraud=int(tp + fn),
        n_detected=int(tp),
        n_missed=int(fn),
        n_false_positives=int(fp),
    )
