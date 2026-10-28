from churn_platform.generator import GeneratorConfig, generate_dataset
from churn_platform.validation import validate_data

def test_clean_baseline_has_no_errors():
    data=generate_dataset(GeneratorConfig(customers=150,months=6,seed=10),inject_anomalies=False)
    issues=validate_data(data)
    assert not (issues.severity=="error").any(), issues.to_string()

def test_required_anomalies_are_detected():
    data=generate_dataset(GeneratorConfig(customers=150,months=6,seed=10),inject_anomalies=True)
    issues=validate_data(data)
    found=set(issues.issue_type)
    assert "churn_label_precedes_prediction_date" in found
    assert "treatment_control_leakage" in found
    assert "offer_sent_to_ineligible_customer" in found
    assert "multiple_offer_attribution" in found

def test_negative_usage_detected():
    data=generate_dataset(GeneratorConfig(customers=20,months=4,seed=4),inject_anomalies=False)
    data["usage_snapshots"].loc[data["usage_snapshots"].index[0],"usage_units"]=-1
    assert "negative_usage" in set(validate_data(data).issue_type)

def test_all_four_anomalies_have_ground_truth_labels():
    data=generate_dataset(GeneratorConfig(customers=80,months=5,seed=33),inject_anomalies=True)
    expected={"churn_label_precedes_prediction_date","offer_sent_to_ineligible_customer","treatment_control_leakage","multiple_offer_attribution"}
    assert expected == set(data["anomaly_ground_truth"].issue_type)

def test_duplicate_primary_key_detected():
    data=generate_dataset(GeneratorConfig(customers=20,months=4,seed=14),inject_anomalies=False)
    data["customers"]=__import__("pandas").concat([data["customers"],data["customers"].iloc[[0]]],ignore_index=True)
    assert "duplicate_primary_key" in set(validate_data(data).issue_type)
