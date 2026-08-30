# Limitations

## Statistical / dataset size

- The model is trained and evaluated on **100 rows with only 11 fraud-labeled examples**. This is far too small for statistically reliable machine-learning metrics; 5-fold stratified cross-validation leaves roughly 2 positive examples per fold. All reported metrics (`evaluation/evaluation_report/metrics.md`) should be read as a demonstration of the approach, not a production-grade performance guarantee, and are explicitly out-of-fold (not the deployed model's in-sample predictions - see `evaluation/run_full_evaluation.py`'s module docstring for why that distinction matters).
- The dataset is a *curated* teaching sample (85 "correct" / 9 "escalate" / 6 "fraud" by `curation_category`), not a random sample of real claims, so the class balance and feature correlations here are not representative of a real book of business.

## Feature/derivation caveats

- `Days_Policy_Accident` / `Days_Policy_Claim` and their `_numeric`/`filing_delay_flag`/`quick_claim_flag` counterparts represent time since **policy inception**, not the accident-to-claim reporting delay their names suggest, and are nearly constant across this sample. The rule engine instead recovers the real filing delay from narrative text where possible (47/100 historical claims have both dates stated exactly enough to compute it) or from user-entered dates for new claims; see `docs/data_documentation.md`.
- `suspicion_score`'s original derivation formula could not be fully reverse-engineered from the 100-row sample. New claims use a simple, documented approximation (`src/fraud_detect/features/derive.py::suspicion_score`); historical claims always replay their real CSV value.
- The Financial Exposure and Vehicle/Claim Pattern rule sub-scores (`Instructions_Set_Reports.docx` &sect;10) are implementer judgment calls - the instructions leave their exact formula open ("consider vehicle value; severity; ..."). The chosen weightings are documented in `docs/model_and_system_explanation.md` but are not derived from the source instructions themselves.
- Dropdown categories in the "New Claim" form are limited to the values observed in the 100-row curated sample (e.g. `VehiclePrice` tops out realistically; a couple of categories like `AgeOfPolicyHolder`'s "21 to 25" bucket don't appear in any historical row). A production system would offer the insurer's full schema.

## Image and narrative analysis

- Only 26 of 100 historical claims have an accident photo; image-based fraud signals are unavailable for the rest.
- Gemini's narrative/image analysis is not independently ground-truthed - there is no labeled dataset of "correct" contradiction flags or damage assessments to validate it against. It is used as a secondary, complementary signal alongside (not instead of) the deterministic rule engine and ML model, both of which remain the auditable source of the numeric risk score and fraud probability.
- `Instructions_Set_Images.docx`'s assumption that images are structured report-card screenshots is incorrect for this dataset (they are real accident photographs) - see `docs/data_documentation.md` and `docs/ai_use_declaration.md` for how this was corrected.

## System design

- `HIGH_FRAUD_RISK` is a decision-support flag, **not a legal finding of fraud** (`Instructions_Set_Reports.docx` &sect;25). A human senior investigator is required to review and decide every escalated claim.
- The rule engine's thresholds (evidence, delay, escalation triggers) are calibrated against this one curated dataset and the instruction documents' suggested starting values; they are not validated against real-world claims data and would need recalibration before any production use.
- The `claim_mapping.csv` report/image-to-row mapping is specific to this exact file layout (`Accident_Reports.docx`'s numbering, the image folder's plain-numeric filenames). Adding new historical claims/reports/images requires re-running `build_mapping.py`/`verify_mapping.py`, not manual editing.
- Streamlit Community Cloud's free tier sleeps after inactivity and has limited memory; the trained model and evaluation artifacts are committed to the repo (not regenerated at runtime) so the deployed app works immediately after a cold start.
