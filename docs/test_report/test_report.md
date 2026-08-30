# Test Report

## Scope

This report covers use-case testing of the deployed Streamlit application (New Claim, Browse Existing
Claims, Evaluation Dashboard pages) plus the automated pytest suite. All test cases below were executed
against the running app (`streamlit run app/streamlit_app.py`) via a live browser session; results shown
are the actual output text captured from that session, not hypothetical examples.

Screenshots corresponding to each case should be captured during the graded live demo session (see
`docs/test_report/screenshots/README.md`) - the exact steps to reproduce each case are given below so they
can be re-run and captured live.

## Automated test suite

```
python -m pytest tests/ -v
```

15 tests, all passing, covering:

| Test file | What it checks |
|---|---|
| `test_mapping.py` | All 100 claims map to a narrative; 26 images map correctly; report-16/row-14 spot check |
| `test_leakage.py` | `FraudFound_P`/`curation_category`/identifiers never appear in the ML feature set |
| `test_scoring.py` | Rule engine: clean claims score low, known-fraud-pattern claims score high, sub-scores respect caps |
| `test_escalation.py` | No single weak factor alone triggers mandatory escalation; combinations do; contradictions force escalation |
| `test_pipeline_smoke.py` | End-to-end pipeline runs on a historical claim and two brand-new claims (clean and suspicious) without a live Gemini call |

## Use-case test cases (live app)

### Case 1 - New Claim, clean/legitimate profile

**Steps:** New Claim page &rarr; fill in a claim with `PoliceReportFiled=Yes`, `WitnessPresent=Yes`,
`PastNumberOfClaims=none`, `Fault=Third Party`, no narrative, no photo &rarr; Analyze Claim.

**Result:** `LEGITIMATE`, fraud probability 0.5%, risk score 8.4/100, confidence High, no risk factors
identified, no contradictions (correctly - no narrative was supplied, so no false contradiction is raised).

### Case 2 - New Claim, suspicious profile (mandatory escalation triggers)

**Steps:** Same page &rarr; `PoliceReportFiled=No`, `WitnessPresent=No`, `PastNumberOfClaims=more than 4`,
`Fault=Policy Holder`, no narrative, no photo &rarr; Analyze Claim.

**Result (captured live):** `ESCALATE`, fraud probability **86.5%**, risk score **61.1/100**, confidence
High. Top reasons: "Complete absence of independent evidence combined with multiple other risk factors",
"No police report", "No witness", "Past claims: more than 4". Recommended actions include requesting
corroborating documentation and independently verifying the accident. Caption correctly notes "Gemini
narrative/image analysis unavailable for this claim" since neither was provided.

*(A follow-up run with an even more extreme profile - additionally `VehiclePrice=more than 69000`,
`BasePolicy=All Perils`, `NumberOfSuppliments=more than 5`, 19-day filing delay - produced
`HIGH_FRAUD_RISK`, 99.5% probability, risk score 94.7/100, with all 5 mandatory escalation triggers firing
simultaneously; see `tests/test_pipeline_smoke.py::test_suspicious_brand_new_claim_triggers_high_fraud_risk`.)*

### Case 3 - Historical claim with narrative + photo, known fraud case

**Steps:** Browse Existing Claims &rarr; select spreadsheet row 14 (Policy 1003, an Acura sports sedan with
an accompanying accident photo).

**Result:** `HIGH_FRAUD_RISK`, fraud probability **99.4%**, risk score 72.3/100, escalation score 85.0/100,
confidence High. Correctly matches ground truth (`FraudFound_P=1`). Top reasons cite the complete absence of
independent evidence, repeat-offender history, extensive supplementary repairs, and - notably - a
**contradiction Gemini identified between the photo's visible damage (assessed as "Severe") and the claim's
structured `severity_bucket` of "Low"** ($13,800 proxy), something the deterministic checker alone would not
have caught since it only compares narrative text to structured fields, not photo content to structured
fields. This is a concrete example of the multimodal layer adding a genuinely new signal beyond both the
rule engine and the narrative-only check.

### Case 4 - Historical claim with a genuine narrative/structured contradiction

**Steps:** Browse Existing Claims &rarr; select spreadsheet row 0 (Policy 7453, Pontiac sedan).

**Result (captured live):** `ESCALATE`, fraud probability 0.0%, risk score 24.2/100, confidence High.
Ground truth is `FraudFound_P=0` / `curation_category=correct` - this is a deliberately-planted
data-quality contradiction, not a fraud case: the narrative text states "a zero overall suspicion score"
worth of evidence while the structured `evidence_score` field is actually 1 (since a witness was present).
The system correctly flags this as a `CONTRADICTION`, which per `Instructions_Set_Reports.docx` &sect;15
mandates escalation regardless of the (very low) fraud probability - demonstrating the system's designed
distinction between "escalation-worthy" (data needs human clarification) and "likely fraudulent" (&sect;9),
rather than conflating the two.

### Case 5 - Historical claim, clean/legitimate with police report

**Steps:** Browse Existing Claims &rarr; select spreadsheet row 36 (Policy 1426, Pontiac sedan, rural,
policyholder at fault).

**Result (captured live):** `LEGITIMATE`, fraud probability 0.6%, risk score 23.2/100, confidence High, no
contradictions. Matches ground truth (`FraudFound_P=0`). Explanation correctly notes that although the
policyholder was at fault and no witness was present, the filed police report "mitigates" those factors -
demonstrating the negative-evidence-reduces-suspicion behavior required by &sect;8 (a claim isn't penalized
merely for having *some* risk factors when independent evidence is present).

### Case 6 - Evaluation Dashboard

**Steps:** Evaluation Dashboard page (reads precomputed `evaluation/evaluation_report/` artifacts, no live
computation).

**Result (captured live):** Out-of-fold ML metrics: accuracy 0.95, precision 0.80, recall 0.727, F1 0.762,
ROC-AUC 0.991, PR-AUC 0.937; 8/11 actual fraud claims detected, 3 missed, 2 false positives. Escalation
performance: 100% of actual fraud cases escalated, 5.6% of legitimate cases escalated, escalation precision
0.688, escalation recall 1.0. Full false-positive/false-negative writeups render correctly with narrative
excerpts and specific reasons for each miss.

## Summary

| Case | Expected behavior | Result |
|---|---|---|
| 1 | Clean claim &rarr; LEGITIMATE | ✅ Pass |
| 2 | Multiple strong red flags, no evidence &rarr; ESCALATE/HIGH_FRAUD_RISK | ✅ Pass |
| 3 | Known fraud case with photo &rarr; HIGH_FRAUD_RISK, matches ground truth | ✅ Pass |
| 4 | Planted contradiction &rarr; ESCALATE regardless of low fraud probability | ✅ Pass |
| 5 | Legitimate claim with police report &rarr; LEGITIMATE despite some risk factors | ✅ Pass |
| 6 | Evaluation dashboard renders precomputed honest (out-of-fold) metrics | ✅ Pass |

All 15 automated tests pass. All 6 live use-case walkthroughs produced the expected tier and matched ground
truth where ground truth was available. No case crashed or produced an accusatory or fabricated statement.
