# Requirements Traceability Matrix

| Requirement | Implementation / evidence | Verification |
|---|---|---|
| Master entities first | `generator.py` creates Customer, Subscription, Offer before dependent histories | `tests/test_generator.py` |
| Deterministic ID conventions | generator ID templates | ID uniqueness/FK tests |
| 20k customers / 18 months configurable | `GeneratorConfig`, CLI defaults | run CLI with 20000/18 |
| Temporal churn evaluation | `temporal_features` and `temporal_outcomes` provide monthly cutoffs; model training uses earlier cutoffs and evaluates at the latest cutoff with customers held out across the split | generate multiple cutoffs; inspect evaluation metadata |
| Fixed seed | NumPy generator seeded by config | `test_reproducibility` |
| Voluntary/involuntary churn | subscription lifecycle simulation | churn type enum checks |
| Plan changes with preserved history | `plan_change_events` records dated transitions; monthly invoices and feature snapshots use the effective plan price | validate event dates and reconcile snapshots/invoices |
| Offer response/non-response tracking | `offer_response_events` records acceptance, decline, no response, and delivery failure; only accepted offers can cause the simulated treatment effect | response/contact integrity and outcome tests |
| Seasonal users and plan cohorts | generator fields and seasonality factor | data dictionary; inspect distributions |
| Pre-prediction features | usage/billing/support cutoff in feature builder | `test_features_have_prediction_cutoff` |
| Eligibility, cost, margin | offer thresholds, effective rules, plan checks, budget and margin checks; validation independently reconciles invoice and sent-offer costs | `billing_amount_mismatch`, `offer_cost_mismatch`, `offer_margin_violation`, eligibility-rule tests |
| Randomized treatment/control | seeded RNG assignment for eligible contacts | anomaly detection tests |
| Ground truth separate | `ground_truth.csv` and `anomaly_ground_truth` table | truth excluded from exported model inputs |
| Four required anomalies | `inject_known_anomalies` | `test_required_anomalies_are_detected` |
| PK/FK, enums, date checks | `validation.py` | validation tests |
| Reproducible export and checksums | pipeline manifest | checksum tests |
| CSV/JSON Lines/SQL/docs/README | `pipeline.py` writes CSV and JSONL per dataset plus executable SQLite seed SQL for the ten core entities | inspect output files and execute seed SQL with SQLite |
| Interactive UI | `dashboard/app.py` | run `streamlit run dashboard/app.py` |
| Public repository | Candidate must create/push public GitHub repository | submission checklist |
| AI prompt history | `prompts/ai_prompt_history.md` | candidate must complete exact prompt log |
