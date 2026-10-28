# Verification Run Summary

Verification date: 2026-10-28
Environment: Windows, project `.venv`, Python 3.10, pytest 8.x.

## Automated checks

- Full test suite: **23 passed** (`.venv/Scripts/python.exe -m pytest -q`, 46.69 seconds).
- The project's test dependency is pinned to `pytest>=8.0,<9` because pytest 9.2.0 on Python 3.10 raised an internal `NodeId._str_cache` error before test execution. The pinned version ran the full suite successfully.
- Python syntax compilation and `git diff --check` were also run during this verification; no source syntax errors or whitespace errors were reported.
- Tests cover arithmetic-corruption detection, offer-response linkage and status consistency, temporal customer-disjoint model evaluation, CSV/JSONL exports, and SQLite seed SQL execution.

## Full-scale reproducibility

The clean baseline was generated twice with the same configuration: 20,000 customers, 18 months, seed `20261022`, and anomaly injection disabled. All 16 generated tables had identical row counts and SHA-256 checksums across the two runs. Both clean runs had zero validation errors.

| Table | Rows |
|---|---:|
| customers | 20,000 |
| subscriptions | 20,000 |
| usage_snapshots | 193,741 |
| billing_events | 193,741 |
| support_cases | 15,959 |
| plan_change_events | 2,403 |
| campaign_contacts | 768 |
| offer_response_events | 392 |
| churn_outcomes | 20,000 |
| retention_outcomes | 768 |
| temporal_features | 172,475 |
| temporal_outcomes | 172,475 |
| features | 20,000 |
| offers | 2 |
| eligibility_rules | 2 |
| anomaly_ground_truth | 0 |
| **Total** | **832,726** |

## Business and integrity reconciliation

- Billing amounts are checked against the plan-price history effective on the invoice date, including preserved plan changes.
- Sent campaign costs are checked against the offer's plan/rule limits, offer date and lifecycle, and required contribution-margin floor.
- Regression tests alter a billing amount and a sent-offer cost and verify that validation reports the matching reconciliation issues.
- Treatment contacts have linked response records with accepted, declined, no-response, or delivery-failed status. Delivery-failed records agree with delivery state; only accepted and delivered treatment offers can trigger the simulated retention effect. Controls receive no response record.

## Export and temporal model checks

- CSV and JSONL exports include the offer-response history, and the source manifest records row counts and file checksums. Empty JSONL tables are exported as zero-byte files.
- The generated SQLite seed script includes the `OfferResponseEvent` table and is executed in the pipeline test.
- The temporal model test verifies training on earlier cutoffs and evaluation on a later cutoff with customers disjoint between training and evaluation cohorts. This is a synthetic baseline, not real-world performance evidence.

## Submission state and limits

- The GitHub remote is `https://github.com/uday617/customer-churn-retention-platform`; GitHub metadata confirmed the repository visibility is **public**.
- `prompts/ai_prompt_history.md` records the prompts visible in this Codex task and notes that prompts from other tools or conversations must be supplied by the candidate. Those unavailable prompts cannot be reconstructed from this repository.
- Local changes still need to be committed and pushed after they are rebased on the remote's latest `main` commit.
- All generated customer data is synthetic. Reproducibility and simulation tests do not establish production churn performance or causal retention lift.
