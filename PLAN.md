# Vehicle Insurance Claim Fraud Detection — College Project Build Plan

## Context

The user has a college-project dataset from an auto-insurance company: `curated_100_claims_with_ground_truth.csv` (100 claims, 57 columns, ground-truth `FraudFound_P`/`curation_category`), `Accident_Reports.docx` (98 narrative writeups), two instruction documents (`Instructions_Set_Reports.docx`, `Instructions_Set_Images.docx`) written to serve as an AI system's operating spec, and `Insurance_Fraud_Investigation_Images/` (26 real accident photos, not the 100). The goal is a working fraud-scoring prototype (structured data + narrative + optional photo → fraud probability, flags, reasons, recommendation), a system-explanation document (plus an enterprise-upgrade-path section), and every artifact the assignment rubric requires (README, architecture diagram, test report with screenshots, limitations, AI-use declaration, data documentation), deployed as a live Streamlit web app.

Two data facts were discovered during exploration that change the naive reading of the instructions and must be encoded correctly:
1. **Report ↔ CSV row mapping**: report number `N` (headed "N. Incident Overview..." or, for 2 fraud cases, "N. ACCIDENT INVESTIGATION REPORT / Incident Overview...") maps to `csv_0based_row_index = N - 2`. Verified: report 16 (79yo, Accura, urban, policyholder-fault, repeat-offender, FraudFound_P=1) matches CSV row index 14 exactly.
2. **Images are real photos, not report cards.** `Instructions_Set_Images.docx` assumes images are structured screenshots with visible checkboxes for police/witness/dates — confirmed false by opening `16.png` (a photographic red-Acura crash scene matching CSV row 14's Make). Images use the same numbering as reports (26 of 100 claims have one). The image-analysis prompt must be corrected to "assess damage severity/plausibility from a photo," not "read data fields off a card" — this deviation gets called out explicitly in the docs (good-faith rubric credit, not hidden).

User decisions locked in before this plan:
- Image + narrative reasoning uses **Google Gemini** (multimodal), key via `.env` locally / Streamlit secrets in deployment. Gemini is NOT the source of the numeric risk score — that stays deterministic/auditable (rule engine + ML model); Gemini narrates, cross-checks contradictions, and explains.
- Live demo = deployed **Streamlit** app on **Streamlit Community Cloud**. I `git init` and commit locally; user creates the GitHub repo, pushes, and connects Streamlit Cloud themselves (account creation/OAuth is not something to automate).
- Gemini analysis for the 100 existing claims is **precomputed once and cached** (data/processed/); the "New Claim" page calls Gemini live.
- ML models: Logistic Regression, Decision Tree, Random Forest, **and XGBoost**, under stratified 5-fold CV (100 rows / 11 positives is small — honest caveats throughout, no metric inflation).

## Repo structure

```
D:\Swasti\
├── data\
│   ├── raw\                                    # existing files, untouched (csv, docx, images already here)
│   └── processed\
│       ├── claim_mapping.csv                   # csv_row_index, report_number, policy_number, has_report, has_image, image_path
│       ├── narratives_extracted.csv            # report_number, csv_row_index, narrative_text, has_alt_fraud_heading
│       └── gemini_cache.json                   # precomputed narrative+image analysis for the 100 existing claims, keyed by csv_row_index
│
├── src\fraud_detect\
│   ├── config.py                               # paths, env loading (.env / st.secrets), column constants
│   ├── data\
│   │   ├── load_csv.py                         # load + schema-validate the 57-col CSV
│   │   ├── extract_narratives.py               # docx paragraph parse, regex ^(\d+)\.\s handles both heading styles
│   │   ├── build_mapping.py                    # builds claim_mapping.csv (single static lookup, no runtime guessing)
│   │   └── verify_mapping.py                   # hard assertions: 100/100 narratives mapped, all 26 images map, report-16 spot check — milestone-1 gate
│   ├── features\
│   │   ├── leakage.py                          # LEAKAGE_COLUMNS = [FraudFound_P, curation_category]; get_feature_columns()
│   │   ├── engineer.py                         # categorical encoding for ML, any extra derived features
│   │   └── consistency_check.py                # deterministic (non-LLM) structured-vs-narrative contradiction detector (§21)
│   ├── rules\
│   │   ├── constants.py                        # every §10 point value as named constants, comment citing doc section
│   │   ├── scoring.py                          # 7 sub-scores (Evidence/History/Reporting/Fault/Financial/Vehicle-Pattern/Statistical) → scale_to_100()
│   │   └── escalation.py                       # §15 mandatory vs recommended triggers, each returns (bool, human-readable reason)
│   ├── ml\
│   │   ├── dataset.py                          # X via get_feature_columns(), y=FraudFound_P (train/eval only)
│   │   ├── train.py                            # LogReg + DecisionTree + RandomForest + XGBoost, StratifiedKFold(5)
│   │   ├── evaluate.py                         # accuracy/precision/recall/F1/ROC-AUC/PR-AUC/confusion matrix (out-of-fold), fraud-recall/precision/FPR
│   │   ├── threshold.py                        # §14 threshold sweep → 4-tier cut points
│   │   └── model_store.py                      # joblib persist model+preprocessor, model_card.json
│   ├── llm\
│   │   ├── gemini_client.py                    # wraps google-generativeai; get_api_key() tries st.secrets then os.environ; retry/timeout/graceful-fail
│   │   ├── system_prompt.py                    # distilled operational prompt from both instruction docs (FACT/INFERENCE/RECOMMENDATION, no-accusation phrasing, demographic-bias ban)
│   │   ├── schemas.py                          # pydantic models for structured Gemini JSON outputs
│   │   ├── narrative_analysis.py               # text-only Gemini call: summary + contradiction candidates
│   │   ├── image_analysis.py                   # multimodal call: damage severity/plausibility (corrected scope vs Instructions_Set_Images.docx)
│   │   └── explanation.py                      # drafts TOP REASONS / NARRATIVE EVIDENCE / CONTRADICTIONS / WHAT TO CHECK; deterministic fallback if Gemini unavailable
│   ├── decision\
│   │   ├── fusion.py                           # rule score + ML prob + escalation triggers + Gemini flags → 4-tier decision (documented ordered algorithm)
│   │   └── why_report.py                       # assembles exact §16 WHY-report field layout
│   ├── cache\
│   │   └── build_gemini_cache.py               # one-off script: runs narrative_analysis+image_analysis for all 100 existing claims → gemini_cache.json
│   └── pipeline.py                             # single orchestration entrypoint: claim → features → rules → ml → llm(optional) → decision → why_report
│
├── app\
│   ├── streamlit_app.py                        # entrypoint
│   ├── pages\
│   │   ├── 1_New_Claim.py                      # structured form + optional narrative + optional image upload → live pipeline
│   │   ├── 2_Browse_Existing_Claims.py         # pick from 100 curated claims, uses cached Gemini results, shows ground truth AFTER prediction
│   │   └── 3_Evaluation_Dashboard.py           # renders precomputed evaluation_report artifacts (no live recompute)
│   ├── components\
│   │   ├── results_view.py                     # risk breakdown, evidence, contradictions, recommendations, downloadable WHY-report
│   │   └── claim_form.py                       # shared structured-field form widgets
│   └── streamlit_helpers.py                    # st.cache_resource for model/Gemini client, secrets indirection
│
├── evaluation\
│   ├── run_full_evaluation.py                  # §27: runs pipeline over all 100 claims w/o touching labels until scoring; writes evaluation_report\
│   ├── generate_fp_fn_writeups.py              # §24: WHY-report-style writeup for every false positive/negative
│   └── evaluation_report\                      # metrics.json/.md, confusion_matrix.png, per_claim_predictions.csv, escalation_performance.md, fp_fn_analysis.md
│
├── docs\
│   ├── README.md
│   ├── architecture_diagram.png (+ mermaid source)
│   ├── model_and_system_explanation.md         # scoring/ML/fusion rationale + explicit "enterprise upgrade path" section
│   ├── limitations.md
│   ├── ai_use_declaration.md                   # Gemini's role + Claude Code used to design/build the system + the corrected image-doc deviation
│   ├── data_documentation.md                   # 57-column breakdown, mapping rule, leak-safety review of pre-engineered columns
│   └── test_report\
│       ├── test_report.md
│       └── screenshots\
│
├── models\                                     # model.joblib, preprocessor.joblib, model_card.json (committed — trivial size at n=100)
├── tests\                                       # test_mapping, test_leakage, test_scoring, test_escalation, test_pipeline_smoke
├── .streamlit\config.toml, secrets.toml.example
├── .env.example
├── .gitignore                                   # .env, secrets.toml, __pycache__, .venv
└── requirements.txt
```

## Key algorithms (decided, documented in code + docs, not left implicit)

- **Rule engine (§10)**: Evidence Risk 0–25 (police absent +10, witness absent +10, both absent +5 more), Claim History 0–15 (categorical `PastNumberOfClaims`: none/1/"2 to 4"/"more than 4" → 0/2/8/15), Reporting Behavior 0–15 using `days_policy_claim_numeric` as the authoritative delay field (narrative-stated delay is a cross-check signal only, not the scored value), Fault 0–10, Financial Exposure 0–15 and Vehicle/Claim Pattern 0–10 as documented weighted composites of existing engineered columns (implementer judgment calls since the doc leaves exact formulas open — written down with rationale in `model_and_system_explanation.md`), Statistical Risk 0–5 from `make_fraud_rate`. Raw max is 95 → single `scale_to_100()` rescale step, documented.
- **Escalation (§15)**: mandatory triggers (total evidence absence + multiple other factors; strong narrative/structured contradiction; extreme financial exposure + weak evidence; repeat-claims + no-evidence + delay combo; suspicion score high; ML-prob high AND rule-score high) force at least ESCALATE; explicit negative guards prevent escalation on any single weak factor alone (make, age, gender, marital status, urban/rural, one past claim, high value alone, high severity alone, missing police report alone).
- **ML**: features = CSV columns minus `{FraudFound_P, curation_category}` minus identifier columns (PolicyNumber/RepNumber); `Make` dropped in favor of the existing leak-safe `make_fraud_rate` (avoids high-cardinality overfit at n=100). StratifiedKFold(5), class_weight='balanced' where applicable, out-of-fold predictions concatenated for one honest confusion matrix, mean±std reported with an explicit small-sample caveat per §13.
- **Fusion**: ML-probability tier from `threshold.py`'s sweep → mandatory-trigger override (forces ≥ESCALATE) → recommended-trigger nudge toward HIGH_FRAUD_RISK when combined with high ML probability. Confidence = agreement/disagreement between rule-tier and ML-tier.
- **Gemini's role**: narrative summary + contradiction candidates (secondary to the deterministic `consistency_check.py`), photo damage/plausibility assessment (corrected scope), and WHY-report prose (FACT/INFERENCE/RECOMMENDATION style, non-accusatory phrasing, never inventing facts) — all with a deterministic template fallback if the API is unavailable/rate-limited.

## Build order (each step gated by verification before moving on)

1. Data layer: `extract_narratives.py` → `build_mapping.py` → `verify_mapping.py` passes (100/100 narratives, 26/26 images, report-16 spot check).
2. Feature/leakage layer: `leakage.py`, `engineer.py`, `consistency_check.py`; `test_leakage.py` passes.
3. Rule engine: `constants.py`, `scoring.py`, `escalation.py`; unit tests against hand-computed examples (e.g. CSV row 14 scores meaningfully higher than a known-clean row).
4. ML: `dataset.py`, `train.py` (4 models, 5-fold CV), `evaluate.py`, `threshold.py`, `model_store.py`; sanity-check fraud recall isn't 0.
5. Fusion + WHY-report (deterministic path only, no Gemini yet): `fusion.py`, `why_report.py`; manually inspect output on 5–10 sample claims.
6. Gemini layer: `gemini_client.py`, `system_prompt.py`, `schemas.py`, `narrative_analysis.py`, `image_analysis.py`, `explanation.py`; confirm graceful fallback with no/invalid API key.
7. `build_gemini_cache.py` precomputes all 100 existing claims → `gemini_cache.json`.
8. Full `pipeline.py` wiring; smoke test with mocked Gemini + one live-API run.
9. Batch evaluation: `run_full_evaluation.py`, `generate_fp_fn_writeups.py` → `evaluation_report\` populated.
10. Streamlit UI: `claim_form.py`, `results_view.py`, 3 pages; manual click-through including the no-narrative/no-image new-claim path.
11. `git init`, `requirements.txt`, `.streamlit/config.toml`, `secrets.toml.example`, `.env.example`, `.gitignore`; verify clean-clone run with only local secrets populated.
12. Documentation pass: README, architecture diagram, model/system explanation (+ enterprise upgrade path), limitations, AI-use declaration, data documentation.
13. Test report: run demo cases (clean legitimate / mandatory-escalation / contradiction / photo-included / brand-new-no-evidence / a known FP or FN), screenshot each into `docs/test_report/screenshots/`, write `test_report.md`.

## Verification

- Automated: `pytest tests/` (mapping, leakage, scoring, escalation, pipeline smoke).
- `python -m fraud_detect.data.verify_mapping` must pass before any other module is trusted.
- `python -m evaluation.run_full_evaluation` produces `evaluation_report/metrics.md` — manually reviewed for honesty (no inflated claims given n=100/11 positives).
- Manual: run `streamlit run app/streamlit_app.py` locally, click through all 3 pages and the demo case list above, capture screenshots for `test_report.md`.
- Final: user pushes the git-init'd repo to their own GitHub and connects Streamlit Community Cloud, pastes the real `GEMINI_API_KEY` into Streamlit secrets, confirms the deployed app loads and a New Claim submission works end-to-end.
