# Screenshots for the live demo

This project's test cases (see `../test_report.md`) were verified against the running app during
development. For your graded submission, capture screenshots of the same 6 cases while giving your live
demo (or from a recorded run) and save them here as `case1.png` ... `case6.png`:

1. **case1.png** - New Claim page, clean profile, result showing `LEGITIMATE`.
2. **case2.png** - New Claim page, suspicious profile (no police report, no witness, more than 4 past
   claims, policyholder fault), result showing `ESCALATE` or `HIGH_FRAUD_RISK`.
3. **case3.png** - Browse Existing Claims, row 14 (Policy 1003), showing the photo, the `HIGH_FRAUD_RISK`
   result, and the Gemini image-analysis contradiction note.
4. **case4.png** - Browse Existing Claims, row 0 (Policy 7453), showing the detected contradiction and
   `ESCALATE` status.
5. **case5.png** - Browse Existing Claims, row 36 (Policy 1426), showing `LEGITIMATE` despite some risk
   factors, because a police report is present.
6. **case6.png** - Evaluation Dashboard, showing the metrics, confusion matrix, and escalation performance.

Exact reproduction steps for each case are in `../test_report.md`.
