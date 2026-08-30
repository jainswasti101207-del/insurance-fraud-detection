# ML Model Performance (out-of-fold cross-validation)

n=100 claims, 11 fraud-labeled.

> out-of-fold cross-validation (ml/train.py) - NOT the deployed model's in-sample predictions, which would be artificially inflated on its own training data.

> 100 rows / 11 fraud-labeled claims is too small for statistically reliable metrics. These numbers describe performance on this curated sample only; see docs/limitations.md.

- accuracy: 0.95
- precision: 0.8
- recall: 0.727
- f1: 0.762
- roc_auc: 0.991
- pr_auc: 0.937
- false_positive_rate: 0.022

Confusion matrix (rows=actual, cols=predicted): [[87, 2], [3, 8]]

Fraud detection: 8/11 detected, 3 missed, 2 false positives.
