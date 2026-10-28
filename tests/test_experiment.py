import pandas as pd
from churn_platform.evaluation import campaign_metrics

def test_lift_and_cost_calculation():
    contacts=pd.DataFrame([
      {"campaign_contact_id":"c1","customer_id":"u1","assigned_group":"treatment","offer_sent":True,"offer_cost":10,"monthly_price":100},
      {"campaign_contact_id":"c2","customer_id":"u2","assigned_group":"treatment","offer_sent":True,"offer_cost":10,"monthly_price":100},
      {"campaign_contact_id":"c3","customer_id":"u3","assigned_group":"control","offer_sent":False,"offer_cost":0,"monthly_price":100},
      {"campaign_contact_id":"c4","customer_id":"u4","assigned_group":"control","offer_sent":False,"offer_cost":0,"monthly_price":100},
    ])
    outcomes=pd.DataFrame([
      {"campaign_contact_id":"c1","customer_id":"u1","retained":True},
      {"campaign_contact_id":"c2","customer_id":"u2","retained":True},
      {"campaign_contact_id":"c3","customer_id":"u3","retained":True},
      {"campaign_contact_id":"c4","customer_id":"u4","retained":False},
    ])
    m=campaign_metrics(contacts,outcomes)
    assert m["retention_lift"] == .5
    assert m["incremental_retained"] == 1
    assert m["offer_cost"] == 20

def test_empty_campaign_is_safe():
    m=campaign_metrics(pd.DataFrame(),pd.DataFrame())
    assert m["treatment_n"] == 0
    assert m["retention_lift"] is None

def test_model_handles_insufficient_data():
    from churn_platform.model import train_evaluate_model
    features=pd.DataFrame([{"customer_id":"u1","last_usage":1,"usage_change_pct":0,"late_or_failed_payments":0,"support_case_count":0,"monthly_price":100,"plan":"basic"}])
    outcomes=pd.DataFrame([{"customer_id":"u1","churned_within_horizon":False}])
    metrics,model=train_evaluate_model(features,outcomes)
    assert metrics["status"]=="insufficient_data"
    assert model is None

def test_model_trains_when_both_classes_available():
    from churn_platform.generator import GeneratorConfig, generate_dataset
    from churn_platform.model import train_evaluate_model
    data=generate_dataset(GeneratorConfig(customers=1200,months=10,seed=20261022),inject_anomalies=False)
    metrics,model=train_evaluate_model(data["features"],data["churn_outcomes"])
    assert metrics["status"]=="ok", metrics
    assert model is not None
    assert 0 <= metrics["precision"] <= 1
    assert 0 <= metrics["recall"] <= 1
