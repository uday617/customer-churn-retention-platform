# Edge-Case Matrix

| ID | Scenario | Expected handling | Implemented check / test |
|---|---|---|---|
| EC-01 | Duplicate primary key | Flag error; preserve source evidence | `duplicate_primary_key`; automated test |
| EC-02 | Null primary key | Flag error | `null_primary_key` |
| EC-03 | Unknown foreign key | Flag error | `foreign_key_violation` |
| EC-04 | Negative usage | Flag error | `negative_usage`; automated test |
| EC-05 | Duplicate subscription/month snapshot | Flag error | `duplicate_monthly_snapshot` |
| EC-06 | Negative invoice amount without refund/credit type | Flag error | `negative_billing_amount` |
| EC-07 | Invalid payment status | Flag error | `invalid_payment_status` |
| EC-08 | Churn future-label date at/before prediction date | Flag temporal error | `churn_label_precedes_prediction_date`; automated test |
| EC-09 | Customer assigned to both groups | Flag experiment-integrity error | `treatment_control_leakage`; automated test |
| EC-10 | Offer sent while ineligible | Flag business-rule error | `offer_sent_to_ineligible_customer`; automated test |
| EC-11 | Customer attributed to multiple offers | Flag attribution error | `multiple_offer_attribution`; automated test |
| EC-12 | Duplicate contact in one generated campaign | Warning for manual inspection; multiple campaigns may be legitimate | `duplicate_customer_contact` warning for injected duplicate IDs |
| EC-13 | No campaign contacts | Pipeline must not crash; dashboard displays empty state | `test_empty_campaign_is_safe`; anomaly injector seeds explicit anomaly fixture only in injected mode |
| EC-14 | Only one class in model evaluation | Return undefined AUC rather than crash | `model_metrics` guards class count |
| EC-15 | Same seed and configuration | Identical generated records/checksums | `test_reproducibility`; full 20k reproducibility smoke check |
| EC-16 | Invalid generator scale or anomaly rate | Fail fast with clear ValueError | `GeneratorConfig` validation; automated tests |
| EC-17 | Missing usage history | Skip feature row rather than invent feature values | feature builder skips missing group |
| EC-18 | Single usage month | Set prior usage equal to last usage, giving zero usage change | feature builder fallback |
| EC-19 | Treatment assignment but offer delivery failure | Retain treatment assignment for intention-to-treat; no offer cost/attribution | campaign simulation and metric logic |
| EC-20 | Control assigned | Offer must not be sent | automated test |
| EC-21 | Offer cost/margin boundary | Contact only when cost cap and margin floor pass | eligibility check; automated test |
| EC-22 | Prediction feature cutoff | Exclude records after prediction date | grouped pre-cutoff usage/billing/support logic; automated test |
| EC-23 | Uncertain / small campaign lift | Display estimate and disclose synthetic uncertainty | dashboard note; no unsupported causal claim |
| EC-24 | Retention outcome on or before prediction date | Flag temporal-integrity error | `outcome_not_after_prediction` |
| EC-25 | Child row has valid customer and subscription IDs that refer to different parents | Flag relationship error | `customer_subscription_mismatch` |
| EC-26 | Retention outcome customer differs from contact customer | Flag relationship error | `customer_contact_mismatch` |
| EC-27 | Unsupported business enum or inconsistent subscription lifecycle | Flag enum/lifecycle error | `invalid_enum`; `invalid_subscription_lifecycle` |
| EC-28 | Control offer sent or cost recorded without successful delivery | Flag experiment/financial error | `control_offer_sent`; `cost_without_delivery` |
| EC-29 | Plan change effective before subscription start or at/after termination | Flag lifecycle error and preserve event | `invalid_plan_change_date` |

## Deliberate anomalies

The generator appends four named negative scenarios to the anomaly-injected dataset and writes the matching records to `ground_truth.csv`. Run with `--no-anomalies` to verify the clean baseline separately. A detected anomaly is not automatically repaired; source history is preserved and validation issues explain the exception.

## Known limits

This matrix documents both implemented automated checks and business conditions that still deserve deeper production hardening. In particular, production use would need confidence intervals/power analysis, offer effective-date enforcement for every contact timestamp, a formal campaign identifier/assignment uniqueness constraint, stronger event lifecycle state-transition checks, and an actual trained model with time-based holdout evaluation. These are not represented as completed functionality.
