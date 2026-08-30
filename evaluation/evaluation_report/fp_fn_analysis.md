# False Positive / False Negative Analysis
Out-of-fold, at threshold 0.5: 2 false positives, 3 false negatives (see docs/limitations.md for small-sample caveats).

## False Positives (legitimate claims flagged as likely fraud)

### Claim row 61 (policy 1313)
- OOF fraud probability: 0.795, rule score: 50.5, actual: legitimate (escalate)
- Why the system thought this was suspicious: PastNumberOfClaims=none, PoliceReportFiled=No, WitnessPresent=No, Fault=Policy Holder, severity_bucket=Medium, make_fraud_rate=0.067.
- Narrative excerpt: Incident Overview & Initial Details On a Friday in the third week of November 1994, an urban accident involved a BMW sedan (Policy Number 1313). The driver was a 53-year-old married male policyholder with a driver rating of 4, carrying an "All Perils" policy on a vehicle valued between $20,000 and $...

### Claim row 69 (policy 58)
- OOF fraud probability: 0.813, rule score: 75.5, actual: legitimate (escalate)
- Why the system thought this was suspicious: PastNumberOfClaims=2 to 4, PoliceReportFiled=No, WitnessPresent=No, Fault=Policy Holder, severity_bucket=High, make_fraud_rate=0.125.
- Narrative excerpt: Incident Overview & Initial Details On a Friday in the second week of November 1994, an urban accident involved an Accura sedan (Policy Number 58). The driver was a 37-year-old single male policyholder with a driver rating of 3, carrying a "Collision" policy on a high-value vehicle priced at over $6...

## False Negatives (fraud claims the system missed)

### Claim row 34 (policy 3940)
- OOF fraud probability: 0.424, rule score: 62.8, actual: fraud
- Why the system missed it: PastNumberOfClaims=2 to 4, PoliceReportFiled=No, WitnessPresent=No, Fault=Policy Holder, severity_bucket=Medium, make_fraud_rate=0.125. Note the system's rule-based escalation logic (mandatory triggers) may still have caught this claim (see final_tier=HIGH_FRAUD_RISK) even where the ML model's cross-validated probability alone did not.
- Narrative excerpt: Incident Overview & Initial Details On Tuesday, May 24, 1994, an auto accident occurred in an urban area involving an Accura sports car operated by a 45-year-old married male policyholder. The driver was assigned policyholder fault for the collision. The vehicle, carrying an estimated midpoint marke...

### Claim row 43 (policy 161)
- OOF fraud probability: 0.315, rule score: 63.2, actual: fraud
- Why the system missed it: PastNumberOfClaims=none, PoliceReportFiled=No, WitnessPresent=No, Fault=Policy Holder, severity_bucket=High, make_fraud_rate=0.056. Note the system's rule-based escalation logic (mandatory triggers) may still have caught this claim (see final_tier=HIGH_FRAUD_RISK) even where the ML model's cross-validated probability alone did not.
- Narrative excerpt: Incident Overview & Initial Details On Friday, December 9, 1994, an auto accident occurred in an urban area involving a Chevrolet sedan operated by a 33-year-old married male policyholder. The driver was assigned policyholder fault for the collision. The high-value vehicle—carrying an estimated midp...

### Claim row 59 (policy 14084)
- OOF fraud probability: 0.409, rule score: 80.7, actual: fraud
- Why the system missed it: PastNumberOfClaims=more than 4, PoliceReportFiled=No, WitnessPresent=No, Fault=Policy Holder, severity_bucket=Medium, make_fraud_rate=0.125. Note the system's rule-based escalation logic (mandatory triggers) may still have caught this claim (see final_tier=HIGH_FRAUD_RISK) even where the ML model's cross-validated probability alone did not.
- Narrative excerpt: Incident Overview & Initial Details On a Wednesday in the third week of August 1996, an urban incident occurred involving an Accura sedan (Policy Number 14084). The driver was a 38-year-old married male policyholder with a driver rating of 4, holding a "Collision" coverage policy on a vehicle valued...
