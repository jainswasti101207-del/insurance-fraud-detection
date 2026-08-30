# Data Documentation

## Sources

| File | Description |
|---|---|
| `data/raw/curated_100_claims_with_ground_truth.csv` | 100 auto-insurance claims, 57 columns. |
| `data/raw/Accident_Reports.docx` | 100 narrative accident-report writeups, one per claim. |
| `data/raw/Insurance_Fraud_Investigation_Images/` | 26 real accident-scene/damage photographs (not all 100 claims have one). |
| `Instructions_Set_Reports.docx` | Master fraud-investigation instruction spec (rule scoring, escalation logic, WHY-report format). Distilled into `src/fraud_detect/llm/system_prompt.py` and implemented directly in `src/fraud_detect/rules/`. |
| `Instructions_Set_Images.docx` | Companion instruction spec for image analysis. Its core assumption - that images are structured "report card" screenshots with checkboxes for police/witness/date fields - is **incorrect for this dataset**; see "Corrected assumption" below. |

## CSV column groups

- **Raw claim fields** (28 columns): `Month`, `WeekOfMonth`, `DayOfWeek`, `Make`, `AccidentArea`, `DayOfWeekClaimed`, `MonthClaimed`, `WeekOfMonthClaimed`, `Sex`, `MaritalStatus`, `Age`, `Fault`, `PolicyType`, `VehicleCategory`, `VehiclePrice`, `PolicyNumber`, `RepNumber`, `Deductible`, `DriverRating`, `Days_Policy_Accident`, `Days_Policy_Claim`, `PastNumberOfClaims`, `AgeOfVehicle`, `AgeOfPolicyHolder`, `PoliceReportFiled`, `WitnessPresent`, `AgentType`, `NumberOfSuppliments`, `AddressChange_Claim`, `NumberOfCars`, `Year`, `BasePolicy`.
- **Pre-engineered features** (24 columns) already computed in the CSV: `vehicle_price_midpoint`, `coverage_multiplier`, `severity_proxy`, `severity_bucket`, `days_policy_accident_numeric`, `days_policy_claim_numeric`, `quick_claim_flag`, `filing_delay_flag`, `past_claims_numeric`, `repeat_offender_flag`, `address_change_numeric`, `recent_address_change_flag`, `no_evidence_flag`, `evidence_score`, `vehicle_age_numeric`, `high_value_vehicle_flag`, `policyholder_age_numeric`, `young_driver_flag`, `suspicion_score`, `fault_x_basepolicy`, `make_fraud_rate`, `month_numeric`, `weekday_numeric`.
- **Ground-truth / leakage columns** (2 columns, never used as model input): `FraudFound_P` (binary, 11/100 positive), `curation_category` (`correct`=85, `escalate`=9, `fraud`=6).

Leak-safety review of the pre-engineered columns: all are deterministic functions of the raw structured fields (vehicle price, coverage, dates, evidence flags, claim history) and do not depend on `FraudFound_P`/`curation_category`. `src/fraud_detect/features/leakage.py` is the single enforced chokepoint (`get_feature_columns()`), and `tests/test_leakage.py` asserts the label never appears in the model's feature set.

`PolicyNumber`/`RepNumber` are excluded as row identifiers. `Make` is excluded from ML features in favor of the already-engineered, leak-safe `make_fraud_rate` (a raw `Make` one-hot would overfit a 10-category column against only 100 rows).

## Claim &harr; report &harr; image mapping

Accident_Reports.docx is a flat sequence of 100 report groups (3 paragraphs each: heading+overview, claim evaluation, blank separator). Each report is headed `"N. Incident Overview & Initial Details"` - except two fraud-labeled reports (16 and 18), headed `"N. ACCIDENT INVESTIGATION REPORT / Incident Overview & Initial Details"` instead.

**Verified mapping rule:** `csv_0based_row_index = report_number - 2` (report 2 &rarr; row 0, report 101 &rarr; row 99). Confirmed by cross-referencing report 16's narrative (79-year-old, Accura, urban, policyholder-fault, repeat-offender, `FraudFound_P: 1`) against CSV row index 14 - an exact match on Make, Age, and fraud label.

Images in `Insurance_Fraud_Investigation_Images/` use plain numeric filenames (`16.png`, `100.jpeg`, etc., no `input_file_` prefix as `Instructions_Set_Images.docx` assumed) and the **same numbering as the reports** - confirmed by opening `16.png`: it shows a damaged red Acura sedan on an urban street, matching CSV row 14's `Make=Accura`. Only 26 of the 100 claims have an image.

This mapping is built once by `src/fraud_detect/data/build_mapping.py` into `data/processed/claim_mapping.csv` and hard-verified by `src/fraud_detect/data/verify_mapping.py` (100/100 narratives mapped, all 26 images mapped, the report-16/row-14 spot check) - every other module reads this static table rather than re-deriving the arithmetic.

## Corrected assumption: images are real photographs, not report cards

`Instructions_Set_Images.docx` describes the images as structured "visual summary report" cards with checkboxes for police/witness status and visible date fields, and provides an illustrative OpenCV skeleton for reading them. This is incorrect for the actual data: the images are genuine accident-scene/vehicle-damage photographs. `src/fraud_detect/llm/image_analysis.py` and its system prompt are written for the corrected task - assessing visible damage severity and plausibility against the claimed accident description - and explicitly instruct Gemini not to attempt reading data fields from the image.

## Known dataset limitations affecting feature derivation

- `Days_Policy_Accident`/`Days_Policy_Claim` (and their `_numeric` counterparts) represent days *since policy inception*, not the accident-to-claim filing delay implied by their names. Both are almost constant across this curated 100-row sample (`Days_Policy_Claim` is `"more than 30"` for all 100 rows), so they carry no real signal here.
- The true accident-to-claim filing delay used by the rule engine's Reporting Behavior sub-score (`Instructions_Set_Reports.docx` &sect;10, indicator 4) is instead recovered from the narrative text when possible (`src/fraud_detect/features/narrative_dates.py`) - exact calendar dates are stated in roughly half the narratives; the other half use a vague "a Weekday in the Nth week of Month Year" phrasing with no day-level precision, so exact delay is recoverable for only 47/100 historical claims. New claims entered through the app always supply exact accident/claim dates, so this limitation only affects the historical replay path, not the live system going forward.
- Several engineered columns' *exact* original derivation formulas could not be fully reverse-engineered from 100 rows alone (notably `suspicion_score`, which depends on more than the fields we could isolate). For historical claims, the CSV's original values are always used as-is. For brand-new claims, `src/fraud_detect/features/derive.py` computes a documented, transparent approximation instead - see the module's docstring for exactly which formulas are exact matches (verified against the data) versus reasonable approximations.
