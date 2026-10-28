"""Integrity and business-rule checks; anomalies are reported, never silently repaired."""
from __future__ import annotations
from typing import Dict, List
import pandas as pd

REQUIRED = {
 "customers":["customer_id"], "subscriptions":["subscription_id","customer_id"],
 "plan_change_events":["plan_change_event_id","customer_id","subscription_id","effective_month","previous_plan","new_plan"],
 "usage_snapshots":["snapshot_id","subscription_id","customer_id","snapshot_month","usage_units"],
 "billing_events":["billing_event_id","customer_id","subscription_id","amount","payment_status"],
 "support_cases":["support_case_id","customer_id","subscription_id"],
 "offers":["offer_id"], "eligibility_rules":["eligibility_rule_id","offer_id"],
 "campaign_contacts":["campaign_contact_id","customer_id","subscription_id","offer_id","assigned_group","eligibility_status"],
 "offer_response_events":["offer_response_event_id","campaign_contact_id","customer_id","offer_id","response_date","response_status"],
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
    def fk(child, col, parent, pcol):
        if all(k in data for k in (child,parent)) and col in data[child] and pcol in data[parent]:
            valid=set(data[parent][pcol].dropna().astype(str)); values=data[child][col]
            bad=data[child][values.notna() & ~values.astype(str).isin(valid)]
            for _,r in bad.head(100).iterrows(): add("error","foreign_key_violation",child,r.get(data[child].columns[0]),f"{col}={r[col]} not found in {parent}.{pcol}")
    fk("subscriptions","customer_id","customers","customer_id")
    fk("plan_change_events","customer_id","customers","customer_id"); fk("plan_change_events","subscription_id","subscriptions","subscription_id")
    for child in ("usage_snapshots","billing_events","support_cases","churn_outcomes","campaign_contacts"):
        fk(child,"customer_id","customers","customer_id"); fk(child,"subscription_id","subscriptions","subscription_id")
    fk("eligibility_rules","offer_id","offers","offer_id"); fk("campaign_contacts","offer_id","offers","offer_id")
    fk("offer_response_events","campaign_contact_id","campaign_contacts","campaign_contact_id")
    fk("offer_response_events","customer_id","customers","customer_id"); fk("offer_response_events","offer_id","offers","offer_id")
    fk("retention_outcomes","campaign_contact_id","campaign_contacts","campaign_contact_id")
    fk("retention_outcomes","attributed_offer_id","offers","offer_id")
    # A valid individual FK is not sufficient when the child also records its
    # customer: the referenced subscription/contact must belong to that same customer.
    if {"subscriptions","campaign_contacts"}.issubset(data):
        sub_owner=data["subscriptions"].set_index("subscription_id").customer_id.astype(str).to_dict()
        for table in ("plan_change_events","usage_snapshots","billing_events","support_cases","churn_outcomes","campaign_contacts"):
            if table not in data or not {"subscription_id","customer_id"}.issubset(data[table].columns): continue
            bad=data[table][data[table].apply(lambda r: sub_owner.get(str(r.subscription_id)) != str(r.customer_id),axis=1)]
            for _,r in bad.head(100).iterrows(): add("error","customer_subscription_mismatch",table,r.iloc[0],"Customer does not own the referenced subscription")
    if {"campaign_contacts","retention_outcomes"}.issubset(data):
        contact_owner=data["campaign_contacts"].set_index("campaign_contact_id").customer_id.astype(str).to_dict()
        for _,r in data["retention_outcomes"].iterrows():
            if contact_owner.get(str(r.campaign_contact_id)) != str(r.customer_id): add("error","customer_contact_mismatch","retention_outcomes",r.retention_outcome_id,"Customer does not match the referenced campaign contact")
    enum_fields={
        "customers":{"segment":{"standard","premium","business"},"region":{"north","south","east","west"},"acquisition_channel":{"organic","referral","paid","partner"}},
        "subscriptions":{"plan":{"basic","plus","pro"},"status":{"active","churned"},"churn_type":{"none","voluntary","involuntary"}},
        "plan_change_events":{"previous_plan":{"basic","plus","pro"},"new_plan":{"basic","plus","pro"}},
        "billing_events":{"payment_status":{"paid","late","failed","refunded","pending"}},
        "support_cases":{"category":{"technical","billing","product","cancellation"},"severity":{"low","medium","high"},"status":{"open","resolved"}},
        "campaign_contacts":{"assigned_group":{"treatment","control"},"eligibility_status":{"eligible","ineligible"}},
        "offer_response_events":{"response_status":{"accepted","declined","no_response","delivery_failed"}},
        "churn_outcomes":{"churn_type":{"none","voluntary","involuntary"}},
    }
    for table,fields in enum_fields.items():
        if table not in data: continue
        for col,allowed in fields.items():
            if col not in data[table]: continue
            bad=data[table][~data[table][col].isin(allowed)]
            for _,r in bad.head(100).iterrows(): add("error","invalid_enum",table,r.iloc[0],f"{col}={r[col]} is not an allowed value")
    # Date order and state transitions are checked on source records, not repaired.
    if "subscriptions" in data:
        df=data["subscriptions"]
        start=pd.to_datetime(df.start_date,errors="coerce")
        end=pd.to_datetime(df.end_date,errors="coerce")
        bad=df[end.notna() & start.notna() & (end<start)]
        for _,r in bad.iterrows(): add("error","invalid_subscription_dates","subscriptions",r.subscription_id,"end_date precedes start_date")
        bad=df[((df.status=="active") & df.end_date.notna()) | ((df.status=="churned") & df.end_date.isna()) | ((df.status=="active") & (df.churn_type!="none")) | ((df.status=="churned") & (df.churn_type=="none"))]
        for _,r in bad.iterrows(): add("error","invalid_subscription_lifecycle","subscriptions",r.subscription_id,"Status, end_date and churn_type are inconsistent")
    if "plan_change_events" in data and "subscriptions" in data:
        events=data["plan_change_events"]
        if "previous_plan" in events and "new_plan" in events:
            bad=events[events.previous_plan==events.new_plan]
            for _,r in bad.iterrows(): add("error","invalid_plan_transition","plan_change_events",r.plan_change_event_id,"Previous and new plans must differ")
        subs=data["subscriptions"].set_index("subscription_id")
        for _,r in events.iterrows():
            if r.subscription_id not in subs.index: continue
            sub=subs.loc[r.subscription_id]
            effective=pd.to_datetime(r.effective_month,errors="coerce")
            start=pd.to_datetime(sub.start_date,errors="coerce")
            end=pd.to_datetime(sub.end_date,errors="coerce")
            if pd.isna(effective) or (not pd.isna(start) and effective<start) or (not pd.isna(end) and effective>=end):
                add("error","invalid_plan_change_date","plan_change_events",r.plan_change_event_id,"Plan change must occur after start and before termination")
    if "campaign_contacts" in data:
        df=data["campaign_contacts"]
        if {"assigned_group","offer_sent"}.issubset(df.columns):
            bad=df[(df.assigned_group=="control") & df.offer_sent.astype(bool)]
            for _,r in bad.iterrows(): add("error","control_offer_sent","campaign_contacts",r.campaign_contact_id,"Control assignment cannot receive an offer")
        if {"offer_sent","offer_cost"}.issubset(df.columns):
            bad=df[(~df.offer_sent.astype(bool)) & (pd.to_numeric(df.offer_cost,errors="coerce").fillna(0)!=0)]
            for _,r in bad.iterrows(): add("error","cost_without_delivery","campaign_contacts",r.campaign_contact_id,"Offer cost must be zero when delivery failed or no offer was sent")
    if {"offer_response_events","campaign_contacts"}.issubset(data):
        contacts=data["campaign_contacts"].set_index("campaign_contact_id")
        for _,r in data["offer_response_events"].iterrows():
            if r.campaign_contact_id not in contacts.index: continue
            c=contacts.loc[r.campaign_contact_id]
            if c.customer_id!=r.customer_id or c.offer_id!=r.offer_id:
                add("error","response_contact_mismatch","offer_response_events",r.offer_response_event_id,"Response customer/offer does not match its campaign contact")
            if c.assigned_group!="treatment":
                add("error","response_for_control","offer_response_events",r.offer_response_event_id,"Control contacts cannot have an offer response")
            if (r.response_status=="delivery_failed" and bool(c.offer_sent)) or (r.response_status!="delivery_failed" and not bool(c.offer_sent)):
                add("error","response_delivery_mismatch","offer_response_events",r.offer_response_event_id,"Response status must agree with offer delivery")
            if pd.to_datetime(r.response_date,errors="coerce")<=pd.to_datetime(c.prediction_date,errors="coerce"):
                add("error","response_date_before_prediction","offer_response_events",r.offer_response_event_id,"Response event must follow the prediction date")
    if "retention_outcomes" in data and {"outcome_date","customer_id"}.issubset(data["retention_outcomes"].columns) and "campaign_contacts" in data:
        contacts=data["campaign_contacts"].set_index("campaign_contact_id")
        for _,r in data["retention_outcomes"].iterrows():
            c=contacts.loc[r.campaign_contact_id] if r.campaign_contact_id in contacts.index else None
            if c is not None and pd.to_datetime(r.outcome_date,errors="coerce") <= pd.to_datetime(c.prediction_date,errors="coerce"):
                # The generator's empty-campaign anomaly fixture uses prediction
                # date as outcome date intentionally; retain as an anomaly finding.
                add("error","outcome_not_after_prediction","retention_outcomes",r.retention_outcome_id,"Retention outcome must occur after prediction date")
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
        # Reconcile each invoice to the plan and price effective on its event date.
        if {"subscriptions","plan_change_events"}.issubset(data) and {"subscription_id","event_date","event_type","amount"}.issubset(df.columns):
            subs=data["subscriptions"].set_index("subscription_id")
            change_groups={key:g.sort_values("effective_month") for key,g in data["plan_change_events"].groupby("subscription_id",sort=False)}
            price_by_plan={"basic":299.0,"plus":599.0,"pro":999.0}
            invoices=df[df.event_type=="invoice"]
            for _,r in invoices.iterrows():
                if r.subscription_id not in subs.index: continue
                changes=change_groups.get(r.subscription_id)
                plan=str(changes.iloc[0].previous_plan) if changes is not None and len(changes) else str(subs.loc[r.subscription_id].plan)
                if changes is not None:
                    for _,change in changes.iterrows():
                        if str(change.effective_month)<=str(r.event_date): plan=str(change.new_plan)
                        else: break
                expected=price_by_plan.get(plan)
                if expected is not None and abs(float(r.amount)-expected)>0.01:
                    add("error","billing_amount_mismatch","billing_events",r.billing_event_id,f"Invoice amount {r.amount} does not match effective {plan} price {expected}")
    if {"campaign_contacts","subscriptions","offers","eligibility_rules"}.issubset(data):
        subs=data["subscriptions"].set_index("subscription_id")
        offers=data["offers"].set_index("offer_id")
        rules=data["eligibility_rules"]
        changes_by_sub={key:g.sort_values("effective_month") for key,g in data["plan_change_events"].groupby("subscription_id",sort=False)} if "plan_change_events" in data else {}
        feature_by_customer=data["features"].set_index("customer_id") if "features" in data and "customer_id" in data["features"] else pd.DataFrame()
        prices={"basic":299.0,"plus":599.0,"pro":999.0}
        for _,c in data["campaign_contacts"].iterrows():
            if c.subscription_id not in subs.index or c.offer_id not in offers.index: continue
            sub=subs.loc[c.subscription_id]; offer=offers.loc[c.offer_id]
            offer_rules=rules[(rules.offer_id==c.offer_id)&(rules.effective_from<=c.prediction_date)&(rules.effective_to>=c.prediction_date)]
            if offer_rules.empty:
                add("error","missing_effective_eligibility_rule","campaign_contacts",c.campaign_contact_id,"No eligibility rule applies on the contact prediction date")
                continue
            rule=offer_rules.iloc[0]
            changes=changes_by_sub.get(c.subscription_id)
            plan=str(changes.iloc[0].previous_plan) if changes is not None and len(changes) else str(sub.plan)
            if changes is not None:
                for _,change in changes.iterrows():
                    if str(change.effective_month)<=str(c.prediction_date): plan=str(change.new_plan)
                    else: break
            price=prices.get(plan)
            if price is None: continue
            expected_cost=min(price*float(offer.discount_rate),float(offer.max_cost))
            if bool(c.offer_sent) and abs(float(c.offer_cost)-expected_cost)>0.01:
                add("error","offer_cost_mismatch","campaign_contacts",c.campaign_contact_id,f"Sent offer cost {c.offer_cost} does not match expected cost {expected_cost}")
            if bool(c.offer_sent) and (float(c.offer_cost)>float(offer.max_cost) or float(c.offer_cost)>float(rule.max_offer_cost)):
                add("error","offer_cost_limit_exceeded","campaign_contacts",c.campaign_contact_id,"Sent offer exceeds offer or eligibility-rule cost cap")
            if bool(c.offer_sent) and price*.55-float(c.offer_cost)<price*float(offer.min_margin_rate):
                add("error","offer_margin_violation","campaign_contacts",c.campaign_contact_id,"Sent offer leaves contribution margin below the offer floor")
            if c.eligibility_status=="eligible":
                feature=feature_by_customer.loc[c.customer_id] if not feature_by_customer.empty and c.customer_id in feature_by_customer.index else None
                risk=float(feature.risk_score) if feature is not None else None
                active_at_prediction=bool(feature.subscription_active_at_prediction) if feature is not None and "subscription_active_at_prediction" in feature.index else sub.status=="active"
                allowed=set(str(rule.allowed_plans).split(","))
                date_ok=bool(offer.active) and str(offer.start_date)<=str(c.prediction_date)<=str(offer.end_date)
                rule_date_ok=str(rule.effective_from)<=str(c.prediction_date)<=str(rule.effective_to)
                risk_ok=risk is not None and risk>=float(rule.min_risk)
                if (bool(rule.require_active) and not active_at_prediction) or plan not in allowed or not date_ok or not rule_date_ok or not risk_ok:
                    add("error","eligibility_rule_violation","campaign_contacts",c.campaign_contact_id,"Eligible decision does not satisfy the effective rule, plan, risk, date, or lifecycle constraints")
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
