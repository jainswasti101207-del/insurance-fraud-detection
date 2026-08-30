# How the System Works

## Overview

The system is an **Insurance Fraud Intelligence and Investigation Assistant**, not a binary fraud
classifier (`Instructions_Set_Reports.docx` &sect;28). For every claim it produces: a fraud probability, an
interpretable 0-100 risk score, an escalation decision, a list of reasons, contradictions between narrative
and structured data, and concrete next steps for a human investigator - never a final fraud determination.

Three independent components feed a final decision:

```
Claim (structured fields + optional narrative + optional photo)
        |
        +--> Rule Engine (deterministic, 0-100 risk score)          --\
        +--> ML Model (trained probability, xgboost)                  +--> Decision Fusion --> WHY-Report
        +--> Gemini (narrative/image analysis, explanation prose)   --/
```

## 1. Rule Engine (`src/fraud_detect/rules/`)

Implements `Instructions_Set_Reports.docx` &sect;10's scoring framework as seven independent, unit-tested
sub-scores:

| Sub-score | Points | Basis |
|---|---|---|
| Evidence Risk | 0-25 | Police report absent (+10), witness absent (+10), both absent (+5 more) |
| Claim History | 0-15 | `PastNumberOfClaims` category (none=0, 1=2, 2-4=8, more than 4=15) |
| Reporting Behavior | 0-15 | Exact accident-to-claim delay in days when known (0-2d=0, 3-7d=5, 8+d=15); falls back to the categorical `filing_delay_flag` when the exact delay can't be determined |
| Fault | 0-10 | Policyholder at fault (+10) vs third party (+0) |
| Financial Exposure | 0-15 | `severity_bucket` (Low=0, Medium=8, High=15) - already blends vehicle value, coverage multiplier, and severity proxy as the instructions ask |
| Vehicle/Claim Pattern | 0-10 | High-value vehicle flag (+5) + supplementary-repair extent (0-10) |
| Statistical Risk | 0-5 | `make_fraud_rate` relative to the dataset mean, capped small per the instructions |

The seven maximums sum to 95 (not 100), a fact stated directly in the instructions; the raw total is
rescaled to a 0-100 risk score in one documented step (`rules/scoring.py::total_risk_score`).

**Escalation logic** (`rules/escalation.py`) separately evaluates &sect;15's mandatory triggers (e.g.
complete absence of independent evidence + 2 or more other risk factors; a detected contradiction; extreme
financial exposure with weak evidence; repeat-claim history + no evidence + delay; risk score &ge;70; high ML
probability *and* high rule score together) - any of which forces at least `ESCALATE` regardless of the ML
probability. It also enforces the instructions' explicit negative guards: no single factor (vehicle make,
age, gender, marital status, urban/rural, one past claim, high value alone, high severity alone, missing
police report alone) ever triggers escalation by itself.

## 2. ML Model (`src/fraud_detect/ml/`)

Four candidate models - Logistic Regression, Decision Tree, Random Forest, and XGBoost - are trained on the
non-leaking feature set (every CSV column except `FraudFound_P`, `curation_category`, `PolicyNumber`,
`RepNumber`, and `Make`; `make_fraud_rate` is used in `Make`'s place) under **stratified 5-fold
cross-validation** - the largest split that still keeps roughly 2 positive examples per fold given only 11
fraud-labeled rows in 100. The model with the best out-of-fold PR-AUC (more informative than ROC-AUC under
heavy class imbalance), tie-broken by recall, is selected, refit on the full 100 rows for deployment, and
persisted with `joblib` alongside a `model_card.json` recording its feature list and CV metrics.

**Threshold selection** (`ml/threshold.py`) sweeps probability thresholds against the out-of-fold
predictions and proposes the four tier cut-points biased toward recall - consistent with the instructions'
framing that missed fraud is costlier than an unnecessary investigation.

## 3. Gemini Layer (`src/fraud_detect/llm/`)

Google Gemini (`gemini-2.5-flash`) provides three narrowly-scoped, non-numeric functions: narrative
summarization/contradiction-flagging, accident-photo damage/plausibility assessment, and WHY-report prose
generation - see `docs/ai_use_declaration.md` for the full scope and safeguards. Every call degrades
gracefully (retries, then a documented deterministic fallback) so the system never crashes or blocks on a
missing key or rate limit.

## 4. Decision Fusion (`src/fraud_detect/decision/fusion.py`)

The final tier is computed in this order:

1. Start from the tier implied by the ML probability against the thresholds from step 2.
2. If any mandatory escalation trigger fired, raise the tier to at least `ESCALATE`.
3. If a mandatory trigger fired *and* the ML probability is also above the top threshold, raise to
   `HIGH_FRAUD_RISK` - a strong combination of independent rule-based and model-based signals.

Confidence is `High` when the rule-engine tier and the ML tier agree, `Medium` when adjacent, `Low` when
they diverge by more than one tier - giving the investigator a signal for when the two independent methods
disagree.

## 5. WHY-Report (`src/fraud_detect/decision/why_report.py`)

Assembles the exact field layout required by &sect;16: claim ID, spreadsheet row, policy number, final
status, fraud probability, risk score, escalation score, confidence, top reasons, supporting evidence,
narrative evidence, contradictions, and concrete (never generic) actions for the senior investigator to
check - each action is drawn from a lookup table mapping specific risk factors to specific verification
steps (`why_report.py::ACTION_MAP`), not a canned "investigate further."

## Evaluation results (this dataset, out-of-fold)

See `evaluation/evaluation_report/metrics.md` for the full, regenerable report. Summary: accuracy 0.95,
precision 0.80, recall 0.73 (8/11 actual fraud detected, 3 missed, 2 false positives). Notably, the rule
engine's mandatory-escalation logic still flagged all 3 of the ML model's false negatives as
`HIGH_FRAUD_RISK` on its own (see `evaluation/evaluation_report/fp_fn_analysis.md`) - direct evidence for
why the system combines a deterministic rule engine with an ML model rather than relying on either alone.

---

# Enterprise Upgrade Path

This is a college-project prototype built on a 100-row curated sample. Converting it into an
enterprise-grade fraud-investigation platform would require, roughly in priority order:

1. **Real, larger, continuously-growing labeled data.** Replace the static CSV/docx pair with a live claims
   database and a document-ingestion pipeline (OCR for scanned police reports, structured intake forms,
   claims-system API integration) so the model can be retrained on thousands of labeled claims instead of
   11 fraud examples.
2. **Model retraining cadence and drift monitoring.** Scheduled retraining as new labeled outcomes arrive;
   monitoring for feature drift (e.g. a new vehicle make, a new fraud pattern) and probability-distribution
   drift that would silently invalidate the current thresholds.
3. **A reviewed, versioned rule-policy store**, not constants in code - so actual investigators (not
   engineers) can propose and approve changes to point values and escalation triggers, with an audit trail
   of who changed what and why, and A/B-style validation before a change goes live.
4. **Human-in-the-loop feedback capture.** Every senior-investigator decision (confirmed fraud, cleared,
   still monitoring) should feed back into the training set, closing the loop the current one-off training
   script can't.
5. **Governance and compliance.** A fair-lending/anti-discrimination review of the model (beyond the
   current "don't use demographics as determinants" rule enforced only in the prompt/rule engine), a formal
   model risk-management sign-off, and regulatory documentation appropriate to the insurer's jurisdiction.
6. **Production-grade case-management UI**, replacing the Streamlit demo with a system integrated into the
   insurer's actual claims workflow, with role-based access control, case assignment, and SLA tracking for
   escalated claims.
7. **Audit logging, PII handling, and access control.** Every Gemini call, every score, and every human
   decision logged immutably; claim PII encrypted at rest and in transit; role-scoped access to raw
   narratives/images/scores.
8. **Scaling and cost control for the LLM layer.** Batching, response caching, and spend controls around
   Gemini calls at real claim volumes (thousands/day rather than one-at-a-time demo usage).
9. **CI/CD and proper secrets management.** Automated testing and deployment pipeline, secrets in a managed
   vault rather than `.env`/`secrets.toml`, and infrastructure-as-code for reproducible environments.
10. **Statistical rigor at scale.** Re-derive the rule engine's judgment-call sub-formulas (Financial
    Exposure, Vehicle/Claim Pattern, `suspicion_score`) from real outcome data instead of the documented
    approximations used here, once enough labeled volume exists to validate them properly.
