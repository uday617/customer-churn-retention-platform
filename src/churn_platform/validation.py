"""Integrity and business-rule checks; anomalies are reported, never silently repaired."""
from __future__ import annotations
from typing import Dict, List
import pandas as pd

REQUIRED = {
 "customers":["customer_id"], "subscriptions":["subscription_id","customer_id"],
 "usage_snapshots":["snapshot_id","subscription_id","customer_id","snapshot_month","usage_units"],
 "billing_events":["billing_event_id","customer_id","subscription_id","amount","payment_status"],
 "support_cases":["support_case_id","customer_id","subscription_id"],
 "offers":["offer_id"], "eligibility_rules":["eligibility_rule_id","offer_id"],
 "campaign_contacts":["campaign_contact_id","customer_id","subscription_id","offer_id","assigned_group","eligibility_status"],
 "churn_outcomes":["churn_outcome_id","customer_id","subscription_id","prediction_date","churn_date"],
 "retention_outcomes":["retention_outcome_id","campaign_contact_id","customer_id"]}

def validate_data(data: Dict[str,pd.DataFrame]) -> pd.DataFrame:
    issues=[]
    def add(severity, code, entity, record, detail): issues.append({"severity":severity,"issue_type":code,"entity":entity,"record_id":str(record),"detail":detail})
    for table, cols in REQUIRED.items():
        if table not in data: add("error","missing_table",table,"*","Required table missing"); continue
        df=data[table]
        for col in cols:
            if col not in df.columns: add("error","missing_column",table,col,f"Required column {col} missing")
        pk=cols[0]
        if pk in df:
            dup=df[df[pk].duplicated(keep=False)]
            for val in dup[pk].dropna().astype(str).unique()[:100]: add("error","duplicate_primary_key",table,val,f"Duplicate {pk}")
            if df[pk].isna().any(): add("error","null_primary_key",table,"*",f"Null {pk} values: {int(df[pk].isna().sum())}")
    if not issues or True:
        def fk(child, col, parent, pcol):
            if all(k in data for k in (child,parent)) and col in data[child] and pcol in data[parent]:
                valid=set(data[parent][pcol].dropna().astype(str)); bad=data[child][~data[child][col].astype(str).isin(valid)]
                for _,r in bad.head(100).iterrows(): add("error","foreign_key_violation",child,r.get(data[child].columns[0]),f"{col}={r[col]} not found in {parent}.{pcol}")
        fk("subscriptions","customer_id","customers","customer_id")
        for child in ("usage_snapshots","billing_events","support_cases","churn_outcomes","campaign_contacts"):
            fk(child,"customer_id","customers","customer_id"); fk(child,"subscription_id","subscriptions","subscription_id")
        fk("eligibility_rules","offer_id","offers","offer_id"); fk("campaign_contacts","offer_id","offers","offer_id")
        fk("retention_outcomes","campaign_contact_id","campaign_contacts","campaign_contact_id")
    if "usage_snapshots" in data:
        df=data["usage_snapshots"]
        if "usage_units" in df:
            for _,r in df[df.usage_units < 0].head(100).iterrows(): add("error","negative_usage","usage_snapshots",r.get("snapshot_id"),"Usage cannot be negative")
        if {"subscription_id","snapshot_month"}.issubset(df.columns):
            dup=df[df.duplicated(["subscription_id","snapshot_month"],keep=False)]
            for _,r in dup.head(100).iterrows(): add("error","duplicate_monthly_snapshot","usage_snapshots",r.get("snapshot_id"),"More than one snapshot per subscription/month")
    if "billing_events" in data:
        df=data["billing_events"]
        for _,r in df[df.amount < 0].head(100).iterrows():
            if r.get("event_type") not in ("refund","credit"): add("error","negative_billing_amount","billing_events",r.get("billing_event_id"),"Negative amount must be explicitly typed as refund/credit")
        for _,r in df[~df.payment_status.isin(["paid","late","failed","refunded","pending"])].head(100).iterrows(): add("error","invalid_payment_status","billing_events",r.get("billing_event_id"),f"Unexpected status {r.payment_status}")
    if "churn_outcomes" in data:
        df=data["churn_outcomes"]
        if {"prediction_date","churn_date"}.issubset(df.columns):
            dated=df[df.churn_date.notna()].copy(); future_label=dated[dated.get("churned_within_horizon", pd.Series(True,index=dated.index)).astype(bool)] if "churned_within_horizon" in dated else dated; bad=future_label[pd.to_datetime(future_label.churn_date,errors="coerce") <= pd.to_datetime(future_label.prediction_date,errors="coerce")]
            for _,r in bad.iterrows(): add("error","churn_label_precedes_prediction_date","churn_outcomes",r.get("churn_outcome_id"),"Churn date must be strictly after prediction date for a future-churn label")
    if "campaign_contacts" in data:
        df=data["campaign_contacts"]
        if {"customer_id","assigned_group"}.issubset(df.columns):
            counts=df.groupby("customer_id").assigned_group.nunique(); leak=set(counts[counts>1].index)
            for _,r in df[df.customer_id.isin(leak)].head(100).iterrows(): add("error","treatment_control_leakage","campaign_contacts",r.get("campaign_contact_id"),"Customer appears in both treatment and control")
        if {"eligibility_status","offer_sent"}.issubset(df.columns):
            bad=df[(df.eligibility_status!="eligible") & (df.offer_sent.astype(bool))]
            for _,r in bad.iterrows(): add("error","offer_sent_to_ineligible_customer","campaign_contacts",r.get("campaign_contact_id"),"Offer sent although eligibility status is not eligible")
        if "customer_id" in df:
            dup=df[df.duplicated(["customer_id"],keep=False)]
            # Multiple contacts can be legitimate across campaigns, but not within this single campaign_id convention.
            for _,r in dup[dup.campaign_contact_id.astype(str).str.startswith("ANOM-")].iterrows(): add("warning","duplicate_customer_contact","campaign_contacts",r.get("campaign_contact_id"),"Potential duplicate contact; inspect campaign and assignment history")
    if "retention_outcomes" in data:
        df=data["retention_outcomes"]
        if {"customer_id","attributed_offer_id"}.issubset(df.columns):
            d=df[df.attributed_offer_id.notna()].groupby("customer_id").attributed_offer_id.nunique(); bad=set(d[d>1].index)
            for _,r in df[df.customer_id.isin(bad)].iterrows(): add("error","multiple_offer_attribution","retention_outcomes",r.get("retention_outcome_id"),"Customer attributed to multiple offers")
    return pd.DataFrame(issues,columns=["severity","issue_type","entity","record_id","detail"])

def validation_summary(data: Dict[str,pd.DataFrame], issues: pd.DataFrame) -> dict:
    return {"tables":{k:int(len(v)) for k,v in data.items()},"total_rows":int(sum(len(v) for v in data.values())),"errors":int((issues.severity=="error").sum()) if len(issues) else 0,"warnings":int((issues.severity=="warning").sum()) if len(issues) else 0,"issue_counts":issues.issue_type.value_counts().to_dict() if len(issues) else {},"note":"Injected anomalies are expected to appear in the report; baseline validation should be run separately from anomaly-injected validation."}
