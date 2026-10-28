# Data Dictionary

All records are synthetic. Required means non-null in the baseline. IDs are immutable strings and primary keys are unique within each entity. Date values use ISO `YYYY-MM-DD`; month snapshots use the first day of month. Money is INR.

| Entity | Field | Type | Required | Allowed values / unit | Uniqueness / validation |
|---|---|---|---|---|---|
| Customer | customer_id | string | yes | `CUS-` + 6 digits | PK, immutable |
| Customer | signup_date | date | yes | ISO date | not after generated observation end |
| Customer | segment | enum | yes | standard, premium, business | enum check |
| Customer | region | enum | yes | north, south, east, west | enum check |
| Customer | acquisition_channel | enum | yes | organic, referral, paid, partner | enum check |
| Customer | seasonal_user | boolean | yes | true/false | derived from generator assignment |
| Subscription | subscription_id | string | yes | `SUB-<customer-id>-01` | PK; FK customer |
| Subscription | customer_id | string | yes | Customer ID | FK; one customer can have multiple subscriptions in schema design |
| Subscription | plan | enum | yes | basic, plus, pro | plan effective at the end of generated history; prior transitions are PlanChangeEvent records |
| Subscription | monthly_price | decimal | yes | INR/month, >= 0 | price effective at the end of generated history; campaign pricing uses the prediction-date feature snapshot |
| Subscription | start_date/end_date | date/null | start yes | ISO date | end >= start; active subscription has null end date |
| Subscription | status | enum | yes | active, churned | lifecycle consistency with end date |
| Subscription | churn_type | enum | yes | none, voluntary, involuntary | none if no churn event in window |
| UsageSnapshot | snapshot_id | string | yes | `SNAP-<subscription-id>-YYYY-MM` | PK |
| UsageSnapshot | subscription_id/customer_id | string | yes | parent IDs | FKs must agree |
| UsageSnapshot | snapshot_month | date | yes | month start | unique with subscription ID |
| UsageSnapshot | usage_units | decimal | yes | non-negative units/month | never negative |
| UsageSnapshot | active_days | integer | yes | 1–31 generated | calendar boundary validation |
| UsageSnapshot | feature_window_end | date | yes | ISO date | cannot exceed prediction cutoff for features used |
| BillingEvent | billing_event_id | string | yes | `BILL-<customer-id>-YYYY-MM` | PK |
| BillingEvent | event_date | date | yes | ISO date | not before subscription start in valid baseline |
| BillingEvent | event_type | enum/string | yes | invoice, refund, credit (extensible) | negative amounts require refund/credit type |
| BillingEvent | amount | decimal | yes | INR | reconcile to source event; invoice amount >= 0 |
| BillingEvent | payment_status | enum | yes | paid, late, failed, refunded, pending | enum check |
| BillingEvent | currency | string | yes | INR | ISO currency code |
| SupportCase | support_case_id | string | yes | `CASE-<customer-id>-YYYY-MM-NN` | PK |
| SupportCase | customer_id/subscription_id | string | yes | parent IDs | FKs |
| SupportCase | created_at | date | yes | ISO date | within observation window |
| SupportCase | category | enum | yes | technical, billing, product, cancellation | enum check |
| SupportCase | severity | enum | yes | low, medium, high | enum check |
| SupportCase | status | enum | yes | open, resolved | enum check |
| Offer | offer_id | string | yes | `OFF-2026-000001` | PK |
| Offer | discount_rate | decimal | yes | 0–1 proportion | boundary check |
| Offer | max_cost | decimal | yes | INR, >= 0 | must respect offer budget |
| Offer | min_margin_rate | decimal | yes | 0–1 proportion | eligibility margin floor |
| Offer | start_date/end_date | date | yes | ISO date | end >= start |
| Offer | active | boolean | yes | true/false | must be active for send date |
| EligibilityRule | eligibility_rule_id | string | yes | RULE-NNN | PK |
| EligibilityRule | offer_id | string | yes | Offer ID | FK |
| EligibilityRule | min_risk | decimal | yes | 0–1 | risk threshold |
| EligibilityRule | allowed_plans | comma-separated string | yes | basic/plus/pro subset | plan must be included |
| EligibilityRule | require_active | boolean | yes | true/false | active state requirement |
| EligibilityRule | max_offer_cost | decimal | yes | INR, >= 0 | must not exceed offer max cost |
| EligibilityRule | effective_from/effective_to | date | yes | ISO date | effective_to >= effective_from |
| CampaignContact | campaign_contact_id | string | yes | CONTACT-... | PK |
| CampaignContact | customer_id/subscription_id/offer_id | string | yes | parent IDs | FKs |
| CampaignContact | prediction_date | date | yes | ISO date | features cutoff precedes future outcome window |
| CampaignContact | assigned_group | enum | yes | treatment, control | immutable assignment; no cross-group leakage |
| CampaignContact | offer_sent | boolean | yes | true/false | control should not receive offer |
| CampaignContact | offer_cost | decimal | yes | INR, >= 0 | cost is zero when not sent in this simulation |
| CampaignContact | eligibility_status | enum | yes | eligible, ineligible | sent offer requires eligible status |
| CampaignContact | eligibility_reason | string | yes | rule outcome explanation | required for traceability |
| CampaignContact | assignment_seed | integer | yes | fixed seed | audit reproducibility |
| OfferResponseEvent | offer_response_event_id | string | yes | `RESPONSE-<customer-id>-YYYY` | PK; one response lifecycle record per treatment contact |
| OfferResponseEvent | campaign_contact_id/customer_id/offer_id | string | yes | parent IDs | FKs; contact must be treatment-assigned and customer/offer must match |
| OfferResponseEvent | response_date | date | yes | ISO date | after prediction date and within the outcome window |
| OfferResponseEvent | response_status | enum | yes | accepted, declined, no_response, delivery_failed | delivery failure must agree with contact delivery; no-response is explicit |
| OfferResponseEvent | simulation_rule | string | yes | documented synthetic process | provenance for response outcome |
| ChurnOutcome | churn_outcome_id | string | yes | `CHURN-<customer-id>-YYYY` | PK |
| ChurnOutcome | customer_id/subscription_id | string | yes | parent IDs | FKs |
| ChurnOutcome | prediction_date | date | yes | ISO date | feature cutoff date |
| ChurnOutcome | churn_date | date/null | optional | ISO date/null | future label must occur after prediction date |
| ChurnOutcome | churned_within_horizon | boolean | yes | true/false | derived from lifecycle simulation |
| ChurnOutcome | churn_type | enum | yes | none, voluntary, involuntary | derived from generated lifecycle |
| ChurnOutcome | label_source | string | yes | documented simulation rule | no independent random labels |
| RetentionOutcome | retention_outcome_id | string | yes | RET-... | PK |
| RetentionOutcome | campaign_contact_id/customer_id | string | yes | parent IDs | FK; contact/customer must match |
| RetentionOutcome | outcome_date | date | yes | ISO date | after prediction date |
| RetentionOutcome | retained | boolean | yes | true/false | derived from simulated behavioral outcome |
| RetentionOutcome | attributed_offer_id | string/null | optional | Offer ID/null | one attribution per customer/outcome policy |
| RetentionOutcome | outcome_source | string | yes | documented simulation rule | auditable provenance |
| PlanChangeEvent | plan_change_event_id | string | yes | `PLAN-<subscription-id>-YYYY-MM` | PK; immutable event ID |
| PlanChangeEvent | customer_id/subscription_id | string | yes | parent IDs | FKs must agree with the subscription owner |
| PlanChangeEvent | effective_month | date | yes | ISO month start | within the active subscription period and before the prediction cutoff |
| PlanChangeEvent | previous_plan/new_plan | enum | yes | basic, plus, pro | must differ; records the transition without overwriting event history |
| PlanChangeEvent | previous_monthly_price/new_monthly_price | decimal | yes | INR/month, non-negative | derived from the plan price schedule |

## Relationships and cardinality

- Customer 1:N Subscription; Subscription 1:N UsageSnapshot, BillingEvent and SupportCase.
- Customer 1:N ChurnOutcome across prediction periods; a generated single-window run currently emits one baseline label per customer.
- Offer 1:N EligibilityRule and CampaignContact.
- Customer 1:N CampaignContact across campaigns; the current generated campaign uses at most one normal contact per customer.
- CampaignContact 1:0..1 RetentionOutcome for a single campaign outcome.
- A customer can have multiple offers across separate campaigns, but attribution must be explicit and deduplicated for any one outcome.
- CampaignContact 1:0..1 OfferResponseEvent; only treatment contacts receive a response event, with accepted, declined, no_response, or delivery_failed recorded explicitly.
- Subscription 1:N PlanChangeEvent; each plan transition is retained as an append-only event, while the Subscription row holds the plan and monthly price effective at the end of generated history.
- Effective dates govern rules and offers. The generated records preserve outcomes and assignment records instead of rewriting them in place.
