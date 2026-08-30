# Escalation Performance

> Escalation decisions here come from the full pipeline (rule engine + escalation logic + the deployed model's in-sample ML probability). The rule engine and escalation logic are not fit to data, so they don't have an in-sample/out-of-sample distinction; only the ML probability component does (see metrics.md for the honest, out-of-fold model-only metrics).

- % of actual fraud cases escalated: 100.0%
- % of legitimate cases escalated: 5.6%
- Escalation precision: 0.688
- Escalation recall: 1.0

## Tier distribution

- LEGITIMATE: 84
- HIGH_FRAUD_RISK: 11
- ESCALATE: 5
