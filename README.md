# Customer Churn & Retention Experiment Platform

A reproducible end-to-end demonstration of churn-risk scoring, offer eligibility, randomized retention experiments, audit trails, and data-quality exception detection. **All data is synthetic.** No external or personal customer data is used.

## Features

- Deterministic synthetic generation for 20,000 customers across 18 months (configurable for a fast starter run).
- Customer, Subscription, UsageSnapshot, BillingEvent, SupportCase, Offer, EligibilityRule, CampaignContact, ChurnOutcome, and RetentionOutcome entities with deterministic IDs and linked parent IDs.
- Pre-prediction feature snapshots, transparent heuristic risk scores, a scikit-learn logistic-regression baseline, eligibility/margin checks, randomized treatment/control assignments, and outcome simulation with a documented treatment effect.
- Four labelled required anomalies: churn label before prediction date, offer sent to an ineligible customer, treatment/control leakage, and multiple-offer attribution.
- CSV exports, source manifest with checksums, separate ground-truth file, validation report, and reproducibility checks.
- Streamlit dashboard with risk, campaign, data-quality and table-explorer views.
- Automated tests for schema presence, IDs, foreign keys, temporal integrity, anomaly detection, reproducibility, configuration validation, and experiment calculations.

## Quick start

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
pip install -e .
pytest -q
streamlit run dashboard/app.py
```

## Generate the full dataset

```bash
PYTHONPATH=src python -m churn_platform.cli --customers 20000 --months 18 --seed 20261022 --output data/generated
```

For Windows PowerShell, set the source path before running the module:

```powershell
$env:PYTHONPATH = "src"
python -m churn_platform.cli --customers 20000 --months 18 --seed 20261022 --output data/generated
```

Use `--no-anomalies` to export a clean baseline and validate it separately. The default command injects labelled anomaly records after generating the valid baseline. `ground_truth.csv` is for test/evaluation use only and must never be used as a prediction feature.

## Business definitions and assumptions

- **Churn:** a subscription termination event. `voluntary` and `involuntary` are distinct types; `none` means no churn event was generated during the observation window.
- **Prediction date:** the end of the penultimate month in the generated history. Features are built only from usage, billing and support records available by that cutoff.
- **Prediction horizon:** the next month. `churned_within_horizon` is derived from the simulated subscription lifecycle, not independently randomized.
- **Risk score:** transparent heuristic baseline in `[0,1]` based on usage change, late/failed payments, and support-case volume. A separate logistic-regression baseline is trained/evaluated on a stratified customer holdout. Because this generated run currently has one prediction window per customer, this is not a true temporal backtest; multiple historical cutoffs and a strictly later test period are required before claiming temporal validation or production readiness.
- **Offer eligibility:** risk threshold, plan allow-list, active subscription at prediction, offer active period, offer cost cap and contribution-margin floor. Ineligible customers are not contacted by the normal campaign flow.
- **Experiment:** eligible contacts are randomly assigned treatment/control using the fixed generator RNG. Assignment is immutable in the generated record. Outcome simulation allows a treatment effect only for sent treatment offers in the next-month churn case.
- **Evaluation:** retention lift is treatment retention rate minus control retention rate, by assigned group (intention-to-treat). Small synthetic runs may have noisy estimates. Confidence intervals and power analysis should precede real business decisions.
- **Profit:** the dashboard shows offer costs and an explicitly labelled contribution proxy. This is not a fully causal incremental-profit estimate because future customer lifetime value, discount duration and counterfactual individual outcomes are unknown.
- **Anomalies:** injected anomalies are deliberate negative scenarios. They should be detected, not silently repaired. Run baseline and anomaly-injected validation separately.

## IDs

- Customer: `CUS-000001`
- Subscription: `SUB-CUS-000001-01`
- Usage snapshot: `SNAP-SUB-CUS-000001-01-2025-01`
- Offer: `OFF-2026-000001`
- Churn outcome: `CHURN-CUS-000001-2026`

IDs are stable strings and parent references must match exactly.

## Outputs

Each generated table is exported as a CSV, along with `source_manifest.json`, `ground_truth.csv`, `validation_issues.csv`, and `validation_summary.json`. The manifest records row counts and SHA-256 file checksums. Regenerate with the same version, configuration and seed to compare outputs.

## Test strategy

```bash
pytest -q
```

Tests are deliberately split by generator/integrity, anomaly validation, and experiment metrics. The injected dataset is expected to produce findings; a clean baseline should not produce errors. The test suite does not claim that a synthetic heuristic is production-ready or that a single experiment proves causality outside its simulation assumptions.

## Limitations

- The generated behavior is synthetic and cannot establish real-world churn rates or offer effectiveness.
- The dashboard defaults to a manageable interactive dataset; the full 20k × 18-month dataset is generated by CLI.
- The heuristic score is a baseline; the logistic-regression model is a first supervised baseline, not production-validated. Evaluation currently uses a customer-level stratified holdout rather than a true later-period temporal backtest.
- Campaign outcomes use a documented simulation rule, not real observed customer outcomes.
- No live email/SMS sending, billing integration, or customer data ingestion is implemented.

## AI use disclosure

See [`prompts/ai_prompt_history.md`](prompts/ai_prompt_history.md). Keep this file updated with prompts submitted to every AI tool used, including any additional tools outside this conversation. Review and understand every generated change before submission.
