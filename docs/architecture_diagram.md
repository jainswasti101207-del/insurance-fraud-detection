# Architecture Diagram

## Live claim-scoring path (New Claim / Browse Existing Claims pages)

```mermaid
flowchart TD
    subgraph Input["Claim Input"]
        A1[Structured form fields]
        A2["Narrative text (optional)"]
        A3["Accident photo (optional)"]
    end

    A1 --> B[pipeline.run_pipeline]
    A2 --> B
    A3 --> B

    B --> C1[Feature derivation\nfeatures/derive.py]
    C1 --> D1[Rule Engine\nrules/scoring.py + escalation.py\n0-100 risk score]
    C1 --> D2[ML Model\nmodels/model.joblib\nfraud probability]
    A2 --> D3[Deterministic contradiction check\nfeatures/consistency_check.py]

    A2 -.narrative.-> E1[Gemini: narrative analysis]
    A3 -.photo.-> E2[Gemini: image analysis]
    D3 --> F[Decision Fusion\ndecision/fusion.py]
    D1 --> F
    D2 --> F
    E1 -.contradictions.-> F

    F --> G[WHY-Report\ndecision/why_report.py]
    E1 -.summary.-> H[Gemini: explanation prose]
    E2 -.damage assessment.-> H
    D1 -.flags.-> H
    D2 -.probability.-> H
    F -.reasons.-> H
    H --> G

    G --> I[Streamlit UI\nresults_view.py]

    style D1 fill:#e8f5e9
    style D2 fill:#e3f2fd
    style E1 fill:#fff3e0
    style E2 fill:#fff3e0
    style H fill:#fff3e0
```

*Green/blue boxes are deterministic and auditable (never call an LLM). Orange boxes are Gemini calls, each
with a documented fallback if unavailable - the system never blocks or crashes without them.*

## Offline training & evaluation path

```mermaid
flowchart LR
    CSV[curated_100_claims_with_ground_truth.csv] --> M1[data/build_mapping.py\n+ verify_mapping.py]
    DOCX[Accident_Reports.docx] --> M1
    IMG[Insurance_Fraud_Investigation_Images/] --> M1
    M1 --> M2[data/processed/claim_mapping.csv\n+ narratives_extracted.csv]

    CSV --> T1[ml/train.py\nStratifiedKFold-5\nLogReg/Tree/RF/XGBoost]
    T1 --> T2[models/model.joblib\n+ model_card.json\n+ thresholds.json]
    T1 --> T3[evaluation_report/oof_predictions.csv\nhonest, out-of-fold]

    M2 --> C1[cache/build_gemini_cache.py]
    C1 --> C2[data/processed/gemini_cache.json]

    M2 --> R1[evaluation/run_full_evaluation.py]
    T3 --> R1
    T2 --> R1
    R1 --> R2[metrics.md/json, confusion_matrix.png,\nper_claim_predictions.csv, escalation_performance.md]
    R2 --> R3[evaluation/generate_fp_fn_writeups.py]
    R3 --> R4[fp_fn_analysis.md]
```
