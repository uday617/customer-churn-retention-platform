import pandas as pd
import pytest
from churn_platform.generator import GeneratorConfig, generate_dataset
from churn_platform.pipeline import frame_checksum

@pytest.fixture(scope="module")
def small():
    return generate_dataset(GeneratorConfig(customers=120,months=6,seed=20261022),inject_anomalies=False)

def test_required_tables_and_ids(small):
    expected={"customers","subscriptions","usage_snapshots","billing_events","support_cases","plan_change_events","offers","eligibility_rules","campaign_contacts","churn_outcomes","retention_outcomes","offer_response_events","features","temporal_features","temporal_outcomes"}
    assert expected.issubset(small)
    for table, pk in [("customers","customer_id"),("subscriptions","subscription_id"),("usage_snapshots","snapshot_id"),("billing_events","billing_event_id"),("support_cases","support_case_id"),("plan_change_events","plan_change_event_id"),("offers","offer_id"),("eligibility_rules","eligibility_rule_id"),("campaign_contacts","campaign_contact_id"),("offer_response_events","offer_response_event_id"),("churn_outcomes","churn_outcome_id"),("retention_outcomes","retention_outcome_id")]:
        assert small[table][pk].notna().all()
        assert small[table][pk].is_unique

def test_foreign_keys(small):
    assert set(small["subscriptions"].customer_id) <= set(small["customers"].customer_id)
    assert set(small["usage_snapshots"].subscription_id) <= set(small["subscriptions"].subscription_id)
    assert set(small["billing_events"].customer_id) <= set(small["customers"].customer_id)
    assert set(small["campaign_contacts"].offer_id) <= set(small["offers"].offer_id)

def test_reproducibility():
    a=generate_dataset(GeneratorConfig(customers=30,months=4,seed=88),False)
    b=generate_dataset(GeneratorConfig(customers=30,months=4,seed=88),False)
    assert {k:frame_checksum(v) for k,v in a.items()} == {k:frame_checksum(v) for k,v in b.items()}

def test_different_seed_changes_data():
    a=generate_dataset(GeneratorConfig(customers=30,months=4,seed=1),False)["customers"]
    b=generate_dataset(GeneratorConfig(customers=30,months=4,seed=2),False)["customers"]
    assert frame_checksum(a) != frame_checksum(b)

def test_config_validation():
    with pytest.raises(ValueError): GeneratorConfig(customers=0)
    with pytest.raises(ValueError): GeneratorConfig(months=1)

def test_features_have_prediction_cutoff(small):
    assert (pd.to_datetime(small["features"].prediction_date) < pd.to_datetime("2026-01-01")).all()
    assert small["features"].risk_score.between(0,1).all()

def test_features_never_use_post_prediction_snapshots(small):
    usage=small["usage_snapshots"].copy()
    usage["feature_window_end"]=pd.to_datetime(usage.feature_window_end)
    billing=small["billing_events"].copy(); billing["event_date"]=pd.to_datetime(billing.event_date)
    support=small["support_cases"].copy(); support["created_at"]=pd.to_datetime(support.created_at)
    for row in small["features"].itertuples(index=False):
        cutoff=pd.Timestamp(row.prediction_date)
        available=usage[(usage.customer_id==row.customer_id)&(usage.feature_window_end<=cutoff)].sort_values("snapshot_month")
        assert not available.empty
        assert abs(float(available.iloc[-1].usage_units)-float(row.last_usage)) < 0.002
        # Feature builder's payment/support counts must only include events at or before the cutoff.
        expected_late=int(billing[(billing.customer_id==row.customer_id)&(billing.event_date<=cutoff)].payment_status.isin(["late","failed"]).sum())
        expected_cases=int((support[(support.customer_id==row.customer_id)&(support.created_at<=cutoff)]).shape[0])
        assert row.late_or_failed_payments==expected_late
        assert row.support_case_count==expected_cases

def test_campaign_control_never_receives_offer(small):
    contacts=small["campaign_contacts"]
    if len(contacts):
        assert not contacts.loc[contacts.assigned_group=="control","offer_sent"].astype(bool).any()
        assert (contacts.loc[~contacts.offer_sent.astype(bool),"offer_cost"]==0).all()

def test_offer_response_history_is_explicit_and_linked():
    data=generate_dataset(GeneratorConfig(customers=1200,months=18,seed=20261022),inject_anomalies=False)
    responses=data["offer_response_events"]
    assert responses.offer_response_event_id.is_unique
    assert set(responses.response_status) <= {"accepted","declined","no_response","delivery_failed"}
    contacts=data["campaign_contacts"].set_index("campaign_contact_id")
    assert set(responses.campaign_contact_id) <= set(contacts.index)
    for row in responses.itertuples(index=False):
        contact=contacts.loc[row.campaign_contact_id]
        assert contact.assigned_group=="treatment"
        assert bool(contact.offer_sent)==(row.response_status!="delivery_failed")
    assert "no_response" in set(responses.response_status)

def test_eligibility_margin_is_respected(small):
    offers=small["offers"].set_index("offer_id")
    subs=small["subscriptions"].set_index("subscription_id")
    for c in small["campaign_contacts"].itertuples(index=False):
        o=offers.loc[c.offer_id]
        sub=subs.loc[c.subscription_id]
        cost=min(float(sub.monthly_price)*float(o.discount_rate),float(o.max_cost))
        margin=float(sub.monthly_price)*.55
        assert cost <= float(o.max_cost)
        assert margin-cost >= float(sub.monthly_price)*float(o.min_margin_rate)
