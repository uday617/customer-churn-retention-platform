"""Evaluation metrics for churn model and randomized retention campaigns."""
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, roc_auc_score, average_precision_score, f1_score

def model_metrics(y_true, scores, threshold=.5):
    y=np.asarray(y_true,dtype=int); p=np.asarray(scores,dtype=float)
    pred=(p>=threshold).astype(int)
    out={"n":int(len(y)),"threshold":float(threshold),"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0))}
    out["roc_auc"]=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None
    out["pr_auc"]=float(average_precision_score(y,p)) if len(np.unique(y))>1 else None
    return out

def campaign_metrics(contacts: pd.DataFrame, outcomes: pd.DataFrame) -> dict:
    """Calculate intention-to-treat metrics while excluding ambiguous duplicate keys.

    Deliberately injected duplicate outcome rows are retained in the source data
    for audit, but must not multiply customers in the campaign metrics. Their
    contact keys are excluded from this calculation and counted in the result.
    """
    base = {
        "treatment_n": 0, "control_n": 0,
        "treatment_retention": None, "control_retention": None,
        "retention_lift": None, "incremental_retained": 0,
        "offer_cost": 0.0, "incremental_profit_proxy": None,
        "excluded_duplicate_contact_keys": 0,
        "excluded_duplicate_outcome_rows": 0,
        "excluded_duplicate_contact_rows": 0,
    }
    if contacts.empty or outcomes.empty:
        return base

    keys = ["campaign_contact_id", "customer_id"]
    missing_c = [k for k in keys if k not in contacts.columns]
    missing_o = [k for k in keys if k not in outcomes.columns]
    if missing_c or missing_o:
        raise ValueError(f"Missing campaign merge keys: contacts={missing_c}, outcomes={missing_o}")

    # Any duplicated key is ambiguous; keep it in source/audit tables but omit
    # the entire key from metrics instead of silently choosing a row.
    dup_out_mask = outcomes.duplicated(keys, keep=False)
    duplicate_outcome_rows = int(dup_out_mask.sum())
    duplicate_outcome_keys = outcomes.loc[dup_out_mask, keys].drop_duplicates()
    clean_outcomes = outcomes.loc[~dup_out_mask].copy()

    dup_contact_mask = contacts.duplicated(keys, keep=False)
    duplicate_contact_rows = int(dup_contact_mask.sum())
    duplicate_contact_keys = contacts.loc[dup_contact_mask, keys].drop_duplicates()
    clean_contacts = contacts.loc[~dup_contact_mask].copy()

    ambiguous_keys = pd.concat([duplicate_outcome_keys, duplicate_contact_keys], ignore_index=True).drop_duplicates()
    if not ambiguous_keys.empty:
        clean_contacts = clean_contacts.merge(ambiguous_keys.assign(_ambiguous=True), on=keys, how="left")
        clean_contacts = clean_contacts.loc[clean_contacts["_ambiguous"].isna()].drop(columns="_ambiguous")
        clean_outcomes = clean_outcomes.merge(ambiguous_keys.assign(_ambiguous=True), on=keys, how="left")
        clean_outcomes = clean_outcomes.loc[clean_outcomes["_ambiguous"].isna()].drop(columns="_ambiguous")

    base["excluded_duplicate_contact_keys"] = int(len(ambiguous_keys))
    base["excluded_duplicate_outcome_rows"] = duplicate_outcome_rows
    base["excluded_duplicate_contact_rows"] = duplicate_contact_rows
    if clean_contacts.empty or clean_outcomes.empty:
        return base

    merged = clean_contacts.merge(clean_outcomes, on=keys, how="inner", validate="one_to_one")
    if merged.empty:
        return base

    groups = merged.groupby("assigned_group").retained.agg(["mean", "count"])
    tn = int(groups.loc["treatment", "count"]) if "treatment" in groups.index else 0
    cn = int(groups.loc["control", "count"]) if "control" in groups.index else 0
    tr = float(groups.loc["treatment", "mean"]) if tn else None
    cr = float(groups.loc["control", "mean"]) if cn else None
    lift = tr - cr if tr is not None and cr is not None else None
    incremental = int(round(lift * tn)) if lift is not None else 0
    cost = float(merged.loc[(merged.assigned_group == "treatment") & merged.offer_sent.astype(bool), "offer_cost"].sum())
    contribution = float(merged.loc[(merged.assigned_group == "treatment") & merged.retained.astype(bool), "monthly_price"].sum() * .55) if "monthly_price" in merged else 0.0
    profit = contribution - cost if tn else None
    base.update({
        "treatment_n": tn, "control_n": cn,
        "treatment_retention": tr, "control_retention": cr,
        "retention_lift": lift, "incremental_retained": incremental,
        "offer_cost": cost, "estimated_treatment_contribution": contribution,
        "incremental_profit_proxy": profit,
        "interpretation": "Randomized intention-to-treat comparison; profit is a proxy and not a causal incremental-profit estimate. Ambiguous duplicate keys are excluded and counted for audit.",
    })
    return base
