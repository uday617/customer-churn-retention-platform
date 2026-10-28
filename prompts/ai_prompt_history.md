# YottaFlex AI --- Customer Churn & Retention Platform

## AI Prompt History, Development Prompt Pack, Debugging Log.

**Purpose:** Maintain a transparent record of prompts and AI-assisted
work for the Customer Churn & Retention Platform.

**Important record-keeping rule:** This document includes (1) summaries
of earlier prompts where exact wording is not fully retained, and (2)
proposed prompts for future development and verification. 

------------------------------------------------------------------------

# Part A --- Development Prompt Sequence

## Prompt 1 --- Requirement Analysis and Acceptance Criteria

I am developing a Customer Churn Prediction and Retention Experiment
Platform for a technical recruitment project.

Before writing code, analyse the complete business requirements and
convert them into an implementation plan.

The platform must identify likely churn from behavioural changes,
evaluate retention offer eligibility, track offer costs, simulate
randomized treatment/control experiments, and measure incremental
retention outcomes.

Create a requirement traceability matrix containing: - Requirement ID
and original requirement. - Business purpose and expected behaviour. -
Relevant entity, module, or component. - Acceptance criteria. -
Positive, negative, boundary, and exception tests. - Validation evidence
required before marking the requirement complete.

Cover all ten core entities, deterministic synthetic data generation,
20,000 customers, 18 months of history, fixed-seed reproducibility,
temporal evaluation, four mandatory anomalies, exports, documentation,
dashboard functionality, and submission requirements.

Identify ambiguities and propose explicit, documented assumptions. Do
not silently omit any requirement. Distinguish mandatory requirements
from recommended enhancements.

Do not implement the application yet. Return the requirement matrix,
assumptions, dependencies, risks, and implementation sequence first.

## Prompt 2 --- Architecture and Technology Selection

Based on the approved requirement matrix, design a maintainable
architecture for the complete platform.

Evaluate a suitable Python stack using pandas, NumPy, scikit-learn,
Streamlit, Plotly, pytest, and a lightweight relational or analytical
database.

Explain the trade-offs for: - Data generation and storage. -
Business-rule enforcement. - Churn model training and inference. -
Campaign assignment and outcome simulation. - Validation and audit
logging. - Dashboard state management. - Testing and reproducibility.

Define module boundaries, interfaces, configuration, data flow, error
handling, and dependency management.

Use a configurable starter dataset and full-scale dataset through the
same generator. Avoid unnecessary infrastructure, paid services,
external APIs, and dependencies that make local execution difficult.

Produce a repository tree and a component responsibility matrix.
Identify which modules depend on others and which interfaces need
automated tests.

Do not claim that a component exists or works until its implementation
has been inspected and executed.

## Prompt 3 --- Relational Schema and Data Dictionary

Design the relational data model for Customer, Subscription,
UsageSnapshot, BillingEvent, SupportCase, Offer, EligibilityRule,
CampaignContact, ChurnOutcome, and RetentionOutcome.

For every entity, define: - Primary key and foreign keys. - Field name,
data type, required/optional status. - Allowed values, units,
uniqueness, and validation rules. - Creation time, effective dates,
lifecycle states, and update semantics where applicable. - Cardinality
and optional relationships. - Derived versus source attributes.

Use the required ID conventions: - CUS-000001 -
SUB-`<customer-id>`{=html}-01 -
SNAP-`<subscription-id>`{=html}-2026-01 - OFF-2026-000001 -
CHURN-`<customer-id>`{=html}-2026

Explain how many-to-many relationships will be represented, how
historical state changes will be preserved, and how duplicate or invalid
relationships will be detected.

Produce SQL DDL, a human-readable data dictionary, and a relationship
summary. Include referential-integrity tests and ensure that anomaly
injection does not accidentally corrupt unrelated records.

## Prompt 4 --- Deterministic Synthetic Data Generator

Implement a configurable synthetic data generator for the platform.

Requirements: - Support a starter dataset and 20,000 customers over 18
months. - Use a configurable random seed, defaulting to 20261022. -
Generate parent entities before dependent records. - Use immutable,
deterministic IDs and valid foreign-key references. - Generate realistic
variation across subscription plans, product cohorts, usage, billing,
support interactions, seasonal behaviour, plan changes, voluntary churn,
involuntary churn, and offer non-response. - Define explicit churn
events and a prediction horizon. - Derive balances, totals, statuses,
labels, and scores from source events rather than independently
generating inconsistent values. - Keep normal baseline data separate
from intentionally injected anomalies. - Export CSV, JSON Lines, and SQL
seed data. - Generate a source manifest and data-generation summary.

Parameterize the generator so changing dataset size does not require a
separate implementation.

Add tests for record counts, distributions, identifier formats,
uniqueness, foreign keys, valid date ordering, allowed enums, derived
values, and reproducibility.

Do not describe the generator as complete until the full-scale output
has been generated and validated.

## Prompt 5 --- Temporal Feature Engineering and Churn Prediction

Implement a leakage-safe churn prediction pipeline.

Define a prediction cutoff and future outcome horizon explicitly. Build
features exclusively from information available at or before the
prediction cutoff.

Candidate features may include: - Usage levels and percentage changes. -
Consecutive periods of declining usage. - Billing failures and payment
delays. - Support case counts and unresolved cases. - Subscription
tenure, plan changes, and seasonal patterns.

Define the churn label from documented source events. Distinguish
voluntary churn from involuntary churn and document any exclusion rules.

Use a suitable baseline model and compare it against a simple heuristic
where meaningful. Include preprocessing, missing-value handling, class
imbalance considerations, and reproducible training.

Implement genuine temporal evaluation using historical training cutoffs
and strictly later evaluation periods. Where appropriate, prevent
customer-level leakage across training and test sets.

Report precision, recall, F1, PR-AUC, confusion matrix, and baseline
comparisons. Explain class imbalance and limitations.

Write tests that deliberately introduce post-cutoff features, churn
labels before the prediction date, missing history, and unseen plans.
The pipeline must detect or safely handle these scenarios rather than
silently accepting leakage.

## Prompt 6 --- Offer Eligibility, Costs, and Decision Traceability

Implement an auditable retention-offer decision engine.

An offer decision must consider: - Customer and subscription lifecycle
status. - Churn-risk criteria. - Offer effective dates and expiry. -
Eligibility rules and campaign restrictions. - Previous contacts and
applicable offer limits. - Offer cost and expected contribution
margin. - Conflicting rules and multiple eligible offers.

Define explicit outcomes for eligible, ineligible, rejected, expired,
conflicting, and manual-review cases as appropriate.

Record the evaluated rules, decision timestamp, decision outcome, reason
codes, relevant offer version, and applicable cost assumptions.

Ensure that a high churn score alone never guarantees offer eligibility.

Add tests for boundary dates, inactive subscriptions, repeated contacts,
conflicting rules, expired offers, zero or negative margins, excessive
discounts, missing rule values, and multiple individually valid but
collectively unprofitable offers.

Preserve decision history rather than overwriting earlier decisions.
Report why an offer was rejected and provide sufficient information for
an analyst to reproduce the decision.

## Prompt 7 --- Randomized Campaigns and Outcome Simulation

Implement campaign assignment and retention-outcome generation.

Randomly assign eligible customers to treatment and control groups using
a reproducible allocation process. Preserve assignments and prevent
accidental group changes.

Define a documented outcome-generation process that starts from customer
risk and behavioural characteristics, with a plausible treatment effect
for eligible customers exposed to an offer. Include offer non-response
and failed delivery.

Generate outcomes from the documented simulation process rather than
assigning independent random churn labels.

Distinguish: - Assignment to treatment. - Successful offer delivery. -
Offer acceptance or response. - Subsequent retention or churn. -
Incremental retention attributable to the randomized treatment
comparison.

Define outcome windows, attribution rules, and treatment/control
contamination checks.

Test duplicate assignments, missing outcomes, failed delivery,
control-group offer leakage, multiple-offer attribution, customers who
churn before treatment, and customers retained without an offer.

Preserve raw events and flag invalid scenarios. Do not silently repair
experimental history or attribute causal impact from simple
correlations.

## Prompt 8 --- Business Metrics and Financial Reconciliation

Implement the evaluation module for churn performance, campaign
effectiveness, and financial outcomes.

Calculate: - Churn rate and customer counts. - Model precision, recall,
and PR-AUC. - Eligible customer counts and offer delivery rates. -
Treatment and control retention rates. - Absolute retention lift and
relative lift, clearly distinguished. - Incremental retained
customers. - Campaign expenditure and discount cost. - Incremental
contribution and net incremental profit. - Data-quality failure and
exclusion rates.

Use a documented attribution policy and ensure that customers and
campaign outcomes are not counted multiple times.

For randomized experiments, report uncertainty where appropriate and
explain sample-size limitations. Do not interpret treatment-group
retention alone as causal evidence.

Reconcile every derived financial metric against its source records.
Test missing costs, refunds, duplicate outcomes, failed deliveries, zero
denominators, negative margins, and insufficient sample sizes.

Use explicit validation and exclusion reason codes. If metrics cannot be
calculated reliably, return a clear warning or unavailable result rather
than a misleading number or an unhandled exception.

## Prompt 9 --- Anomaly Injection and Ground Truth

Implement the four mandatory labelled anomaly scenarios: 1. Churn label
precedes the prediction date. 2. Offer is sent to an ineligible
customer. 3. Treatment/control leakage occurs. 4. A retained customer is
attributed to multiple offers.

Generate valid baseline data first, then inject anomalies in a
controlled and reproducible manner.

Maintain a separate ground_truth.csv or JSON file containing anomaly
identifiers, issue types, expected decisions, and expected validation
results. Ground truth must never be included in model input features.

Expand coverage to include additional data-quality, lifecycle, temporal,
eligibility, financial, campaign, and attribution boundary cases.

For each anomaly, specify: - The injected condition. - The detection
rule. - The expected action. - The relevant validation result. - The
automated regression test.

Ensure that anomaly injection is isolated and that unaffected records
remain valid. Do not silently overwrite source events or remove
anomalies merely to make validation pass.

## Prompt 10 --- Interactive Streamlit Dashboard

Implement an interactive Streamlit dashboard for the churn and retention
platform.

Provide: - Configurable customer count, history duration, and random
seed. - An anomaly-injection toggle. - A working Generate/Refresh Data
button. - Overview metrics and subscription-status distribution. -
Churn-risk distribution and customer-level risk exploration. - Offer
eligibility decisions and rejection reasons. - Campaign
treatment/control comparison. - Retention lift, campaign cost, and
incremental-profit reporting. - Data-quality findings, ground-truth
anomalies, and audit information. - A data explorer with filters and
relevant exports.

Every control must affect the underlying computation or explicitly
documented configuration. Changing the customer-count slider and
generating data must update the dataset and every dependent metric
consistently.

Use a clear Streamlit state-management strategy. Prevent stale cached
data from being displayed after regeneration. Validate that all tabs
consume the same generated dataset and that changing the seed produces
the expected new data.

Handle empty datasets, missing metrics, duplicate outcomes, invalid
inputs, and unavailable model results gracefully.

Add tests for the underlying dashboard logic where practical. Also
provide a manual browser-verification checklist for interactions that
cannot be reliably tested through unit tests alone.

## Prompt 11 --- Automated Test Suite and Acceptance Audit

Build a comprehensive automated test suite for the entire application.

Organize tests by: - Schema and data dictionary. - Primary-key and
foreign-key integrity. - ID conventions and naming. - Date ordering and
lifecycle transitions. - Arithmetic reconciliation and derived fields. -
Feature cutoff and temporal leakage. - Model evaluation. - Offer
eligibility and cost constraints. - Treatment/control assignment. -
Outcome generation and attribution. - Ground-truth anomaly detection. -
CSV, JSON Lines, and SQL exports. - Dashboard calculations and state. -
Deterministic reproducibility.

For each acceptance criterion, link at least one test or an explicit
manual verification procedure.

Use realistic fixtures and boundary-value tests. Test both valid
workflows and deliberate failures.

Run the complete test suite. When a failure occurs, identify the root
cause, make the smallest appropriate fix, and rerun the failed test and
the relevant regression suite. After all fixes, rerun the complete
suite.

Report actual test counts, failures, skipped tests, and unresolved
limitations. Never claim tests passed without execution evidence.

## Prompt 12 --- Reproducibility, Performance, and Full-Scale Verification

Verify that the platform works at the required scale.

Generate the full 20,000-customer, 18-month dataset twice in clean runs
using the same configuration and seed.

Compare: - Entity row counts. - File manifests and SHA-256 checksums. -
Primary-key uniqueness. - Foreign-key integrity. - Churn rates and
churn-type distributions. - Cohort, seasonal, and offer-response
coverage. - Ground-truth anomaly counts. - Derived metrics and financial
reconciliation. - Validation summaries.

Investigate any unexpected difference. Distinguish intentionally
variable metadata, if any, from data that must be deterministic.

Test runtime, memory use, export correctness, and dashboard
responsiveness where practical.

Document how to reproduce the run and include a verification report
containing the commands executed, observed outputs, and any limitations.

Do not report reproducibility as verified merely because the same seed
is configured. Compare the actual generated artifacts.

## Prompt 13 --- Packaging, Installation, and Windows Compatibility

Audit the package configuration and Windows setup instructions.

Inspect pyproject.toml, build-system settings, package discovery,
dependencies, import paths, and Streamlit entry points.

Verify that a clean virtual environment can install the project and its
test dependencies. Test the documented commands from the repository
root.

Check that: - Editable installation works where supported. - Imports
resolve correctly. - Streamlit launches from the documented command. -
pytest discovers and runs the intended tests. - Generated outputs go to
documented locations. - No local absolute paths or undeclared
dependencies are required.

Reproduce installation failures before changing configuration. Explain
the root cause of each error and provide minimal, verified fixes.

Do not claim Windows compatibility until the relevant commands have
actually been executed on Windows or the remaining platform-specific
uncertainty has been clearly disclosed.

## Prompt 14 --- Final Code Review and Submission Readiness

Perform a final requirement-by-requirement review of the complete
repository.

Check implementation against the original project specification, data
dictionary, business rules, edge-case matrix, and acceptance criteria.

Inspect: - Correctness and maintainability. - Error handling and
exception paths. - SQL schema and export integrity. - Data leakage and
evaluation methodology. - Offer eligibility and cost enforcement. -
Experiment randomization and attribution. - Dashboard behaviour. -
Automated tests and reproducibility. - Documentation, installation, and
performance. - Secrets, personal information, and licensing. - AI
prompt-history completeness.

Produce a final matrix with PASS, FAIL, and NOT VERIFIED statuses and
evidence for each item.

Identify any remaining gaps explicitly. Do not mark a requirement as
passed based solely on documentation or the existence of a test.

Prepare a submission checklist covering the public GitHub repository,
README, execution instructions, test results, prompt history, meaningful
commits, limitations, and explanation of AI assistance.

The final output must reflect what was actually implemented and
verified, not what was intended.

------------------------------------------------------------------------

# Part B --- Debugging and Issue Resolution Log

## B1. Installation and Packaging Issue

**Observed error:** `pip install -e .` failed with a message indicating
that `setup.py` or `setup.cfg` was missing and that the installed pip
version required a setuptools-based build for editable installation.

**Investigation:** The project contained a `pyproject.toml` defining a
PEP 517 build system with `setuptools.build_meta`. The installed pip
version was 21.2.3.

**Proposed resolution:**

``` powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[test]"
```

**Verification status:** The commands were recommended, but successful
installation was not confirmed in the available conversation.

## B2. Streamlit Command Not Found

**Observed error:** PowerShell reported that `streamlit` was not
recognized as a command.

**Likely cause:** Streamlit was unavailable through the active virtual
environment's command path or had not been installed successfully.

**Proposed resolution:**

``` powershell
python -m pip install streamlit plotly
python -m streamlit --version
python -m streamlit run dashboard/app.py
```

Using `python -m streamlit` invokes Streamlit through the active Python
interpreter.

**Verification status:** The user subsequently displayed the dashboard,
confirming that the application launched at a later point. Full
installation reproducibility and all dashboard interactions were not
verified.

## B3. Campaign Metrics Merge Error

**Observed error:**

`pandas.errors.MergeError: Merge keys are not unique in right dataset; not a one-to-one merge`

**Location:** `src/churn_platform/evaluation.py`, inside
`campaign_metrics()`.

**Failing operation:**

``` python
contacts.merge(
    outcomes,
    on=["campaign_contact_id", "customer_id"],
    how="inner",
    validate="one_to_one"
)
```

**Investigation:** The merge validation indicated duplicate keys in at
least one input. The project intentionally supports a
duplicate-retention-attribution anomaly, making this a relevant scenario
to investigate. The traceback alone does not prove that the injected
anomaly was the sole cause.

**Resolution approach:** Preserve the original outcome records, identify
duplicate attribution keys, exclude ambiguous records from the affected
metrics, and expose the exclusion count and reason in the audit output.
Do not silently delete source records.

**Regression test required:** Construct duplicate outcome keys, verify
that the function does not crash, confirm that ambiguous records remain
available for auditing, and verify that the resulting metrics do not
double-count retained customers.

**Verification status:** A corrected file was provided during the
conversation. The user's local execution of the corrected file and its
regression test was not confirmed.

## B4. Python Indentation Error

**Observed error:** `IndentationError: unexpected indent` on line 1 of
`evaluation.py`.

**Investigation:** The displayed source location suggested that the file
began with an unexpectedly indented assignment. The complete local file
was not available for inspection, so the exact cause could not be
conclusively established.

**Resolution approach:** Replace the complete file contents with the
corrected implementation, preserving the module docstring and imports at
the correct indentation level.

**Verification commands:**

``` powershell
python -m py_compile src/churn_platform/evaluation.py
python -m pytest -q
python -m streamlit run dashboard/app.py
```

**Verification status:** The corrected file was provided, but successful
execution of these commands on the user's machine was not confirmed.

## B5. Dashboard Configuration Not Updating Metrics

**Observed behaviour:** The customer-count slider showed 250, while the
dashboard continued displaying 1,000 customers, subscriptions, and
scored customers.

**Investigation:** This suggested that the displayed data did not
correspond to the current configuration. Potential causes include a
Generate/Refresh action not being triggered, stale Streamlit session
state, cached data, or the configured customer count not being passed to
the generator.

**Expected behaviour:** After generating data with 250 customers, all
customer-dependent metrics should consistently reflect the new dataset.
Subscription counts may differ if the generator permits multiple
subscriptions per customer.

**Verification procedure:**

1.  Set the customer count to 250.
2.  Click Generate/Refresh Data.
3.  Confirm the generated customer count.
4.  Check that all dashboard tabs use the same generated dataset.
5.  Change the seed and regenerate.
6.  Confirm that the new data is consistent with the updated
    configuration.

**Verification status:** The mismatch was observed in a screenshot. A
definitive code-level fix and subsequent successful verification were
not established.

## B6. General Regression Testing Procedure

For each subsequent issue:

1.  Capture the full traceback and reproduce the failure.
2.  Identify the root cause from the relevant source code and inputs.
3.  Make the smallest safe correction.
4.  Add a regression test that covers the original failure.
5.  Run the focused test.
6.  Run the relevant regression tests.
7.  Run the full test suite.
8.  Verify the affected workflow manually when required.
9.  Record the actual results and any remaining limitations.

Do not mark an issue resolved solely because a code change has been
proposed.

------------------------------------------------------------------------
