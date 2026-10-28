# Requirements Traceability Matrix

| Requirement | Implementation / evidence | Verification |
|---|---|---|
| Master entities first | `generator.py` creates Customer, Subscription, Offer before dependent histories | `tests/test_generator.py` |
| Deterministic ID conventions | generator ID templates | ID uniqueness/FK tests |
| 20k customers / 18 months configurable | `GeneratorConfig`, CLI defaults | run CLI with 20000/18 |
| Fixed seed | NumPy generator seeded by config | `test_reproducibility` |
| Voluntary/involuntary churn | subscription lifecycle simulation | churn type enum checks |
| Seasonal users and plan cohorts | generator fields and seasonality factor | data dictionary; inspect distributions |
| Pre-prediction features | usage/billing/support cutoff in feature builder | `test_features_have_prediction_cutoff` |
| Eligibility, cost, margin | offer thresholds, plan checks, budget and margin check | review generator logic; add rule tests as rules evolve |
| Randomized treatment/control | seeded RNG assignment for eligible contacts | anomaly detection tests |
| Ground truth separate | `ground_truth.csv` and `anomaly_ground_truth` table | truth excluded from exported model inputs |
| Four required anomalies | `inject_known_anomalies` | `test_required_anomalies_are_detected` |
| PK/FK, enums, date checks | `validation.py` | validation tests |
| Reproducible export and checksums | pipeline manifest | checksum tests |
| CSV/JSON/SQL/docs/README | `pipeline.py`, schema, dictionary, README | manual output check |
| Interactive UI | `dashboard/app.py` | run `streamlit run dashboard/app.py` |
| Public repository | Candidate must create/push public GitHub repository | submission checklist |
| AI prompt history | `prompts/ai_prompt_history.md` | candidate must complete exact prompt log |
